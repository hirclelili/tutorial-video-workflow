#!/usr/bin/env python3
"""Create reusable workbench data from one confirmed media file and word transcript."""

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
        output.append({"id": f"s-{si}", "start": start, "end": end, "words": words})
    return output


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", required=True, type=Path)
    parser.add_argument("--media", required=True, type=Path)
    parser.add_argument("--transcript", required=True, type=Path)
    parser.add_argument("--title")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    project, media, transcript = (p.expanduser().resolve() for p in (args.project, args.media, args.transcript))
    if not media.is_file():
        parser.error(f"media not found: {media}")
    if not transcript.is_file():
        parser.error(f"transcript not found: {transcript}")
    output = project / "workbench" / "project.json"
    if output.exists() and not args.force:
        parser.error(f"workbench already exists: {output}; use --force to archive and recreate it")
    segments = normalize_segments(json.loads(transcript.read_text(encoding="utf-8")))
    if not segments:
        parser.error("transcript contains no segments")
    asset_id = "primary"
    clips = []
    audio = []
    captions = []
    for index, segment in enumerate(segments, 1):
        link = f"rough-{index}"
        label = "".join(word["text"] for word in segment["words"])[:24] or f"片段 {index}"
        base = {"sourceStart": segment["start"], "sourceEnd": segment["end"], "enabled": True, "linkId": link}
        clips.append({"id": f"v-{index}", "assetId": asset_id, "label": label, "speed": 1.0, "volume": 1.0, **base})
        audio.append({"id": f"a-{index}", "assetId": asset_id, "label": label, "volume": 1.0, **base})
        captions.append({"id": f"c-{index}", "text": "".join(w["text"] for w in segment["words"]), **base})
    now = datetime.now(timezone.utc).isoformat()
    data = {
        "schemaVersion": 1, "projectId": str(uuid.uuid4()), "title": args.title or media.stem,
        "createdAt": now, "updatedAt": now, "status": "editing",
        "assets": [{"id": asset_id, "name": media.name, "path": str(media), "type": "video", "duration": probe_duration(media)}],
        "transcript": {"language": "zh", "segments": segments},
        "tracks": {"video": clips, "audio": audio, "captions": captions},
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
