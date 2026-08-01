#!/usr/bin/env python3
"""Create reusable workbench data from confirmed primary and supporting media."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def probe_duration(media: Path) -> float | None:
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", str(media)],
            check=True, capture_output=True, text=True,
        )
        return float(json.loads(result.stdout)["format"]["duration"])
    except (OSError, subprocess.SubprocessError, KeyError, ValueError, json.JSONDecodeError):
        return None


def normalize_segments(raw: dict[str, Any]) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for si, segment in enumerate(raw.get("segments", []), 1):
        start = float(segment.get("start", 0))
        end = float(segment.get("end", start))
        words = []
        for wi, word in enumerate(segment.get("words") or [], 1):
            text = str(word.get("word", word.get("text", "")))
            words.append({
                "id": f"w-{si}-{wi}", "text": text,
                "start": float(word.get("start", start)), "end": float(word.get("end", end)),
                "deleted": False,
            })
        if not words and segment.get("text"):
            words = [{"id": f"w-{si}-1", "text": str(segment["text"]), "start": start, "end": end, "deleted": False}]
        output.append({"id": f"s-{si}", "start": start, "end": end, "deleted": False, "words": words})
    return output


def load_auto_cuts(path: Path | None, asset_id: str) -> list[dict[str, Any]]:
    if path is None:
        return []
    raw = json.loads(path.read_text(encoding="utf-8"))
    items = raw.get("cuts", []) if isinstance(raw, dict) else raw
    if not isinstance(items, list):
        raise ValueError("auto cut list must be a list or an object containing cuts")
    cuts = []
    for index, item in enumerate(items, 1):
        start, end = float(item["start"]), float(item["end"])
        if end > start:
            cuts.append({"id": str(item.get("id", f"auto-cut-{index}")), "assetId": str(item.get("assetId", asset_id)), "start": start, "end": end})
    return cuts


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", required=True, type=Path)
    parser.add_argument("--media", required=True, action="append", type=Path, help="Repeat for every confirmed media file; the first is primary.")
    parser.add_argument("--transcript", required=True, type=Path)
    parser.add_argument("--auto-cut-list", type=Path, help="Optional JSON cuts already produced by the automatic rough-cut stage.")
    parser.add_argument("--title")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    project = args.project.expanduser().resolve()
    media_files = [path.expanduser().resolve() for path in args.media]
    transcript = args.transcript.expanduser().resolve()
    auto_cut_list = args.auto_cut_list.expanduser().resolve() if args.auto_cut_list else None
    missing = next((path for path in media_files if not path.is_file()), None)
    if missing:
        parser.error(f"media not found: {missing}")
    if not transcript.is_file():
        parser.error(f"transcript not found: {transcript}")
    if auto_cut_list and not auto_cut_list.is_file():
        parser.error(f"auto cut list not found: {auto_cut_list}")
    output = project / "workbench" / "project.json"
    if output.exists() and not args.force:
        parser.error(f"workbench already exists: {output}; use --force to archive and recreate it")
    segments = normalize_segments(json.loads(transcript.read_text(encoding="utf-8")))
    if not segments:
        parser.error("transcript contains no segments")
    media = media_files[0]
    asset_id = "media-1"
    timeline_start = min(segment["start"] for segment in segments)
    timeline_end = max(segment["end"] for segment in segments)
    clips = [{
        "id": "v-1", "assetId": asset_id, "label": media.stem,
        "sourceStart": timeline_start, "sourceEnd": timeline_end,
        "enabled": True, "linkId": "rough-1", "speed": 1.0, "volume": 1.0,
    }]
    audio = [{
        "id": "a-1", "assetId": asset_id, "label": f"{media.stem} 音频",
        "sourceStart": timeline_start, "sourceEnd": timeline_end,
        "enabled": True, "linkId": "rough-1", "volume": 1.0,
    }]
    captions = []
    for index, segment in enumerate(segments, 1):
        label = "".join(word["text"] for word in segment["words"])[:24] or f"片段 {index}"
        captions.append({
            "id": f"c-{index}", "text": "".join(w["text"] for w in segment["words"]),
            "sourceStart": segment["start"], "sourceEnd": segment["end"],
            "enabled": True, "linkId": f"caption-{index}", "label": label,
        })
    now = datetime.now(timezone.utc).isoformat()
    data = {
        "schemaVersion": 2, "projectId": str(uuid.uuid4()), "title": args.title or media.stem,
        "createdAt": now, "updatedAt": now, "status": "editing",
        "assets": [{
            "id": f"media-{index}", "name": path.name, "path": str(path), "type": "video",
            "duration": probe_duration(path), "role": "primary" if index == 1 else "supporting",
            "inTimeline": index == 1,
        } for index, path in enumerate(media_files, 1)],
        "transcript": {"language": "zh", "assetId": asset_id, "segments": segments},
        "tracks": {"video": clips, "audio": audio, "captions": captions},
        "cuts": load_auto_cuts(auto_cut_list, asset_id),
        "jianyingExport": {"status": "not_configured", "templatePath": None, "lastRequest": None},
        "history": {"confirmedRevision": None},
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    (output.parent / "revisions").mkdir(exist_ok=True)
    if output.exists():
        shutil.copy2(output, output.parent / "revisions" / f"project-before-recreate-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json")
    (project / "previews" / "workbench").mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Workbench project: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
