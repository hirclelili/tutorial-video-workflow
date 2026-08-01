#!/usr/bin/env python3
"""Perform static checks on an editable JianYing/CapCut draft folder."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def collect_materials(content: dict[str, Any]) -> list[dict[str, Any]]:
    materials = content.get("materials", {})
    found: list[dict[str, Any]] = []
    if isinstance(materials, dict):
        for kind, entries in materials.items():
            if isinstance(entries, list):
                for entry in entries:
                    if isinstance(entry, dict):
                        found.append({"kind": kind, **entry})
    return found


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("draft", type=Path)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()

    draft = args.draft.expanduser().resolve()
    report_path = args.report.expanduser().resolve() if args.report else draft / "validation.json"
    errors: list[str] = []
    warnings: list[str] = []

    required = [draft / "draft_content.json", draft / "draft_meta_info.json"]
    for path in required:
        if not path.is_file():
            errors.append(f"missing required file: {path.name}")

    content: dict[str, Any] = {}
    meta: dict[str, Any] = {}
    if not errors:
        try:
            content = json.loads(required[0].read_text(encoding="utf-8"))
            meta = json.loads(required[1].read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(f"invalid draft JSON: {exc}")

    tracks = content.get("tracks", []) if isinstance(content, dict) else []
    if not isinstance(tracks, list) or not tracks:
        errors.append("draft has no timeline tracks")
        tracks = []

    segments = [segment for track in tracks if isinstance(track, dict)
                for segment in track.get("segments", []) if isinstance(segment, dict)]
    if tracks and not segments:
        errors.append("timeline tracks contain no segments")

    materials = collect_materials(content)
    missing_media: list[str] = []
    media_count = 0
    text_count = 0
    for material in materials:
        if material.get("kind") == "texts" or material.get("type") in {"text", "subtitle"}:
            text_count += 1
        raw_path = material.get("path")
        if isinstance(raw_path, str) and raw_path:
            media_count += 1
            if not Path(raw_path).expanduser().is_file():
                missing_media.append(raw_path)
    if missing_media:
        errors.extend(f"missing referenced media: {path}" for path in missing_media)
    if text_count == 0:
        warnings.append("no editable text materials found; captions may be absent or baked")
    if media_count == 0:
        warnings.append("no local media paths found in materials")

    material_ids = {str(item.get("id")) for item in materials if item.get("id")}
    dangling = [str(segment.get("material_id")) for segment in segments
                if segment.get("material_id") and str(segment.get("material_id")) not in material_ids]
    if dangling:
        errors.append(f"{len(dangling)} timeline segments reference missing material IDs")

    report = {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "draft": str(draft),
        "static_pass": not errors,
        "manual_open_required": True,
        "summary": {
            "tracks": len(tracks),
            "segments": len(segments),
            "materials": len(materials),
            "media_paths": media_count,
            "editable_text_materials": text_count,
            "meta_present": bool(meta),
        },
        "errors": errors,
        "warnings": warnings,
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Static validation: {'PASS' if not errors else 'FAIL'}")
    print("Manual open in the target JianYing/CapCut version is still required.")
    print(f"Report: {report_path}")
    return 0 if not errors else 2


if __name__ == "__main__":
    raise SystemExit(main())
