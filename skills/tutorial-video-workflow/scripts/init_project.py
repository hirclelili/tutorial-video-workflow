#!/usr/bin/env python3
"""Initialize one confirmed, non-destructive editable-video project."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


MEDIA_EXTENSIONS = {
    ".mp4", ".mov", ".mkv", ".m4v", ".webm",
    ".wav", ".mp3", ".m4a", ".aac", ".flac",
    ".png", ".jpg", ".jpeg", ".webp",
}


def inventory(source: Path) -> list[dict[str, object]]:
    items: list[dict[str, object]] = []
    for path in sorted(source.rglob("*")):
        if path.is_file() and path.suffix.lower() in MEDIA_EXTENSIONS:
            stat = path.stat()
            items.append({
                "path": str(path.resolve()),
                "name": path.name,
                "extension": path.suffix.lower(),
                "bytes": stat.st_size,
                "role": "unclassified",
            })
    return items


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--project", required=True, type=Path)
    parser.add_argument("--goal", required=True)
    parser.add_argument("--primary", required=True, type=Path)
    parser.add_argument("--supporting", action="append", default=[], type=Path)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    source = args.source.expanduser().resolve()
    project = args.project.expanduser().resolve()
    if not source.is_dir():
        parser.error(f"source directory does not exist: {source}")
    if not args.goal.strip():
        parser.error("goal must not be empty")

    primary = args.primary.expanduser().resolve()
    if not primary.is_file():
        parser.error(f"confirmed primary media does not exist: {primary}")
    supporting = [path.expanduser().resolve() for path in args.supporting]
    missing_supporting = [path for path in supporting if not path.is_file()]
    if missing_supporting:
        parser.error(f"confirmed supporting media does not exist: {missing_supporting[0]}")

    manifest_path = project / "workflow" / "project.json"
    if manifest_path.exists() and not args.force:
        parser.error(f"project already initialized: {manifest_path}; use --force to refresh inventory")

    for relative in (
        "workflow", "work/transcripts", "work/proxies", "work/clips",
        "work/generated_assets", "workbench/revisions", "previews/plan", "previews/content",
        "previews/rough_cut", "previews/visual", "previews/capcut_v1",
        "previews/workbench", "previews/capcut_v2", "deliverables/capcut_v1_rough_cut",
        "deliverables/workbench_review", "deliverables/capcut_v2_refined",
    ):
        (project / relative).mkdir(parents=True, exist_ok=True)

    previous = {}
    if manifest_path.exists():
        previous = json.loads(manifest_path.read_text(encoding="utf-8"))

    manifest = {
        "schema_version": 2,
        "created_at": previous.get("created_at", datetime.now(timezone.utc).isoformat()),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "source_root": str(source),
        "project_root": str(project),
        "request": {
            "goal": args.goal.strip(),
            "primary_media": str(primary),
            "supporting_media": [str(path) for path in supporting],
            "output_count": 1,
            "confirmed": True,
        },
        "assets": inventory(source),
        "timeline": previous.get("timeline", []),
        "versions": previous.get("versions", []),
        "review_policy": {
            "require_explicit_approval": True,
            "preserve_prior_versions": True,
            "states_file": "workflow/reviews.json",
        },
        "gates": previous.get("gates", {
            "capcut_v1_static": "pending",
            "capcut_v1_opened": "pending",
            "openchatcut_handoff": "pending",
            "capcut_v2_static": "pending",
            "capcut_v2_opened": "pending",
        }),
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Initialized {project}")
    print(f"Inventoried {len(manifest['assets'])} media files without copying sources")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
