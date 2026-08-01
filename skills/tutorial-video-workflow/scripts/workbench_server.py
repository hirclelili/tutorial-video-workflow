#!/usr/bin/env python3
"""Serve the bundled rough-cut workbench and persist one local project safely."""

from __future__ import annotations

import argparse
import json
import mimetypes
import os
import shutil
import subprocess
import tempfile
import threading
import time
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse


def validate(data: Any) -> dict[str, Any]:
    if not isinstance(data, dict) or data.get("schemaVersion") not in {1, 2}:
        raise ValueError("unsupported workbench project schema")
    if not isinstance(data.get("assets"), list) or not isinstance(data.get("tracks"), dict):
        raise ValueError("project is missing assets or tracks")
    for name in ("video", "audio", "captions"):
        if not isinstance(data["tracks"].get(name), list):
            raise ValueError(f"track is missing: {name}")
    data.setdefault("jianyingExport", {"status": "not_configured", "templatePath": None, "lastRequest": None})
    data.setdefault("cuts", [])
    data.setdefault("roughCutSuggestions", [])
    return data


def deleted_ranges(data: dict[str, Any]) -> list[tuple[float, float]]:
    transcript_asset = data.get("transcript", {}).get("assetId")
    ranges = [(float(w["start"]), float(w["end"])) for s in data["transcript"]["segments"] for w in s["words"] if w.get("deleted")]
    ranges.extend((float(cut["start"]), float(cut["end"])) for cut in data.get("cuts", []) if not transcript_asset or cut.get("assetId") == transcript_asset)
    ranges.sort()
    merged: list[list[float]] = []
    for start, end in ranges:
        if merged and start <= merged[-1][1] + .03:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    return [(a, b) for a, b in merged]


def effective_chunks(data: dict[str, Any]) -> list[dict[str, Any]]:
    cuts = deleted_ranges(data)
    chunks = []
    for clip in data["tracks"]["video"]:
        if clip.get("enabled") is False:
            continue
        parts = [(float(clip["sourceStart"]), float(clip["sourceEnd"]))]
        clip_cuts = cuts if clip.get("assetId") == data.get("transcript", {}).get("assetId") else []
        for cut_start, cut_end in clip_cuts:
            next_parts = []
            for start, end in parts:
                if cut_end <= start or cut_start >= end:
                    next_parts.append((start, end))
                else:
                    if cut_start > start + .025:
                        next_parts.append((start, cut_start))
                    if cut_end < end - .025:
                        next_parts.append((cut_end, end))
            parts = next_parts
        for start, end in parts:
            if end - start >= .04:
                chunks.append({
                    "assetId": clip["assetId"], "start": start, "end": end,
                    "clipStart": float(clip["sourceStart"]), "clipEnd": float(clip["sourceEnd"]),
                    "linkId": clip.get("linkId", clip["id"]), "speed": float(clip.get("speed", 1)),
                })
    return chunks


def has_audio(path: Path) -> bool:
    result = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a:0", "-show_entries", "stream=index", "-of", "csv=p=0", str(path)], capture_output=True, text=True)
    return result.returncode == 0 and bool(result.stdout.strip())


def atempo(speed: float) -> str:
    factors = []
    while speed < .5:
        factors.append(.5); speed /= .5
    while speed > 2:
        factors.append(2.0); speed /= 2
    factors.append(speed)
    return ",".join(f"atempo={x:.6g}" for x in factors)


def srt_time(seconds: float) -> str:
    millis = round(seconds * 1000)
    hours, millis = divmod(millis, 3_600_000)
    minutes, millis = divmod(millis, 60_000)
    secs, millis = divmod(millis, 1000)
    return f"{hours:02}:{minutes:02}:{secs:02},{millis:03}"


def write_srt(data: dict[str, Any], chunks: list[dict[str, Any]], target: Path) -> None:
    all_words = [w for segment in data["transcript"]["segments"] for w in segment["words"]]
    transcript_asset = data.get("transcript", {}).get("assetId")
    captions = {c.get("linkId"): c for c in data["tracks"]["captions"] if c.get("enabled") is not False}
    cursor = 0.0
    entries = []
    emitted_edited: set[str] = set()
    for chunk in chunks:
        speed = chunk["speed"]
        original = "" if chunk["assetId"] != transcript_asset else "".join(w["text"] for w in all_words if w["start"] >= chunk["clipStart"] - .02 and w["end"] <= chunk["clipEnd"] + .02).strip()
        active = "" if chunk["assetId"] != transcript_asset else "".join(w["text"] for w in all_words if not w.get("deleted") and w["start"] >= chunk["start"] - .02 and w["end"] <= chunk["end"] + .02).strip()
        edited = str(captions.get(chunk["linkId"], {}).get("text", "")).strip()
        custom = edited and edited != original
        text = edited if custom and chunk["linkId"] not in emitted_edited else active
        if custom:
            emitted_edited.add(chunk["linkId"])
        length = (chunk["end"] - chunk["start"]) / speed
        if text:
            entries.append((cursor, cursor + length, text))
        cursor += length
    body = "\n\n".join(f"{i}\n{srt_time(start)} --> {srt_time(end)}\n{text}" for i, (start, end, text) in enumerate(entries, 1))
    target.write_text(body + ("\n" if body else ""), encoding="utf-8")


def export_review(data: dict[str, Any], project_root: Path) -> Path:
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        raise RuntimeError("需要 FFmpeg 和 ffprobe 才能导出审片视频")
    assets = {a["id"]: Path(a["path"]).expanduser().resolve() for a in data["assets"]}
    chunks = effective_chunks(data)
    if not chunks:
        raise RuntimeError("当前时间线没有可导出的片段")
    paths = [assets[c["assetId"]] for c in chunks]
    if any(not p.is_file() for p in paths):
        raise RuntimeError("有素材文件已经移动或丢失")
    audio = all(has_audio(p) for p in paths)
    cmd = ["ffmpeg", "-y"]
    for path in paths:
        cmd += ["-i", str(path)]
    filters = []
    concat_inputs = []
    for i, chunk in enumerate(chunks):
        start, end, speed = chunk["start"], chunk["end"], chunk["speed"]
        filters.append(f"[{i}:v]trim=start={start}:end={end},setpts=(PTS-STARTPTS)/{speed}[v{i}]")
        concat_inputs.append(f"[v{i}]")
        if audio:
            filters.append(f"[{i}:a]atrim=start={start}:end={end},asetpts=PTS-STARTPTS,{atempo(speed)}[a{i}]")
            concat_inputs.append(f"[a{i}]")
    filters.append("".join(concat_inputs) + f"concat=n={len(chunks)}:v=1:a={1 if audio else 0}[vout]" + ("[aout]" if audio else ""))
    out_dir = project_root / "previews" / "workbench"
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = int(time.time())
    output = out_dir / f"rough_cut_{stamp}.mp4"
    subtitle = out_dir / f"rough_cut_{stamp}.srt"
    write_srt(data, chunks, subtitle)
    cmd += ["-filter_complex", ";".join(filters), "-map", "[vout]"]
    if audio:
        cmd += ["-map", "[aout]"]
    cmd += ["-c:v", "libx264", "-preset", "veryfast", "-crf", "25", "-c:a", "aac", "-movflags", "+faststart", str(output)]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError("FFmpeg 导出失败：" + result.stderr[-600:])
    return output


def make_handler(project_file: Path, asset_root: Path):
    project_root = project_file.parent.parent

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt: str, *args: object) -> None:
            print(f"[workbench] {fmt % args}")

        def send_bytes(self, body: bytes, content_type: str, status: int = 200) -> None:
            self.send_response(status); self.send_header("Content-Type", content_type); self.send_header("Cache-Control", "no-store"); self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)

        def json_response(self, value: Any, status: int = 200) -> None:
            self.send_bytes(json.dumps(value, ensure_ascii=False).encode(), "application/json; charset=utf-8", status)

        def load_project(self) -> dict[str, Any]:
            return validate(json.loads(project_file.read_text(encoding="utf-8")))

        def persist_project(self, data: dict[str, Any]) -> None:
            revisions=project_file.parent/"revisions"; revisions.mkdir(exist_ok=True)
            if project_file.exists(): shutil.copy2(project_file,revisions/f"project-{int(time.time()*1000)}.json")
            fd,temp=tempfile.mkstemp(prefix="workbench-",suffix=".json",dir=project_file.parent)
            with os.fdopen(fd,"w",encoding="utf-8") as f: json.dump(data,f,ensure_ascii=False,indent=2); f.write("\n")
            os.replace(temp,project_file)

        def do_GET(self) -> None:
            path = urlparse(self.path).path
            if path == "/api/project":
                return self.json_response(self.load_project())
            if path.startswith("/api/media/"):
                asset_id = unquote(path.removeprefix("/api/media/")); data = self.load_project(); asset = next((a for a in data["assets"] if a["id"] == asset_id), None)
                if not asset:
                    return self.json_response({"error": "unknown asset"}, 404)
                return self.serve_file(Path(asset["path"]).expanduser().resolve(), ranges=True)
            relative = "index.html" if path == "/" else path.removeprefix("/assets/") if path.startswith("/assets/") else ""
            target = (asset_root / relative).resolve()
            if not relative or asset_root not in target.parents:
                return self.json_response({"error": "not found"}, 404)
            self.serve_file(target)

        def serve_file(self, target: Path, ranges: bool = False) -> None:
            if not target.is_file():
                return self.json_response({"error": "file not found"}, 404)
            size = target.stat().st_size; start, end = 0, size - 1; status = HTTPStatus.OK
            if ranges and self.headers.get("Range", "").startswith("bytes="):
                spec = self.headers["Range"][6:].split(",", 1)[0]; left, right = spec.split("-", 1); start = int(left or 0); end = min(int(right) if right else size - 1, size - 1); status = HTTPStatus.PARTIAL_CONTENT
            self.send_response(status); self.send_header("Content-Type", mimetypes.guess_type(target.name)[0] or "application/octet-stream"); self.send_header("Cache-Control", "no-store"); self.send_header("Accept-Ranges", "bytes"); self.send_header("Content-Length", str(end-start+1))
            if status == HTTPStatus.PARTIAL_CONTENT:self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
            self.end_headers()
            with target.open("rb") as f:
                f.seek(start); remaining=end-start+1
                while remaining:
                    chunk=f.read(min(1024*1024,remaining))
                    if not chunk:break
                    try:
                        self.wfile.write(chunk)
                    except (BrokenPipeError, ConnectionResetError):
                        break
                    remaining-=len(chunk)

        def do_PUT(self) -> None:
            if urlparse(self.path).path != "/api/project": return self.json_response({"error":"not found"},404)
            try:
                length=int(self.headers.get("Content-Length","0")); data=validate(json.loads(self.rfile.read(length))); project_file.parent.mkdir(parents=True,exist_ok=True)
                self.persist_project(data); self.json_response({"saved":True})
            except (ValueError,json.JSONDecodeError,OSError) as exc:self.json_response({"error":str(exc)},400)

        def do_POST(self) -> None:
            path=urlparse(self.path).path
            if path == "/api/export-jianying":
                data=self.load_project()
                if data.get("status") != "confirmed":
                    return self.json_response({"error":"请先点击“确认当前剪辑”，再导出剪映工程。"},409)
                request_dir=project_root/"workflow";request_dir.mkdir(parents=True,exist_ok=True);request_path=request_dir/"jianying_export_request.json"
                request={"requestedAt":time.strftime("%Y-%m-%dT%H:%M:%S%z"),"workbenchProject":str(project_file),"status":"waiting_for_native_template","templatePath":data["jianyingExport"].get("templatePath"),"requirements":["editable_video_track","editable_audio_track","editable_caption_track","self_contained_media"]}
                request_path.write_text(json.dumps(request,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
                data["jianyingExport"].update({"status":"waiting_for_native_template","lastRequest":str(request_path)});self.persist_project(data)
                if not data["jianyingExport"].get("templatePath"):
                    return self.json_response({"error":"导出请求已保存。请先在当前剪映版本中新建一个空白项目，并让 Codex 将它设置为原生模板；之后再次点击此按钮。","request":str(request_path)},409)
                return self.json_response({"error":"已找到原生模板，但当前环境还没有可验证的 CapCut Mate 导出器。不会使用已知与剪映 10.9 不兼容的旧导出器。","request":str(request_path)},501)
            if path != "/api/export-review": return self.json_response({"error":"not found"},404)
            try:
                output=export_review(self.load_project(),project_root); self.json_response({"file":str(output)})
            except (RuntimeError,OSError,subprocess.SubprocessError) as exc:self.json_response({"error":str(exc)},500)
    return Handler


def main() -> int:
    parser=argparse.ArgumentParser();parser.add_argument("--project",required=True,type=Path);parser.add_argument("--host",default="127.0.0.1");parser.add_argument("--port",type=int,default=8765);parser.add_argument("--open",action="store_true");args=parser.parse_args()
    project_root=args.project.expanduser().resolve();project_file=project_root/"workbench"/"project.json";asset_root=Path(__file__).resolve().parent.parent/"assets"/"workbench"
    if not project_file.is_file():parser.error(f"workbench project not found: {project_file}")
    server=ThreadingHTTPServer((args.host,args.port),make_handler(project_file,asset_root));url=f"http://{args.host}:{server.server_address[1]}";print(f"Workbench: {url}",flush=True)
    if args.open:threading.Timer(.4,lambda:webbrowser.open(url)).start()
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:server.server_close()
    return 0


if __name__=="__main__":raise SystemExit(main())
