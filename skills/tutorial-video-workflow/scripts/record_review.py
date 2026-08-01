#!/usr/bin/env python3
"""Record an explicit user decision for a versioned stage preview."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


STAGES = {"plan", "content", "rough_cut", "visual", "capcut_v1", "openchatcut", "capcut_v2"}
STATUSES = {"approved", "changes_requested", "skipped"}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", required=True, type=Path)
    parser.add_argument("--stage", required=True, choices=sorted(STAGES))
    parser.add_argument("--status", required=True, choices=sorted(STATUSES))
    parser.add_argument("--preview", action="append", default=[], type=Path)
    parser.add_argument("--note", default="")
    args = parser.parse_args()

    project = args.project.expanduser().resolve()
    project_manifest = project / "workflow" / "project.json"
    if not project_manifest.is_file():
        parser.error(f"project is not initialized: {project_manifest}")

    previews = [path.expanduser().resolve() for path in args.preview]
    missing = [path for path in previews if not path.is_file()]
    if missing:
        parser.error(f"preview does not exist: {missing[0]}")
    if args.status != "skipped" and not previews:
        parser.error("approved or changes_requested reviews require at least one preview")
    if args.status == "skipped" and not args.note.strip():
        parser.error("skipped reviews require a reason in --note")

    review_path = project / "workflow" / "reviews.json"
    if review_path.exists():
        data = json.loads(review_path.read_text(encoding="utf-8"))
    else:
        data = {"schema_version": 1, "reviews": []}

    prior = [item for item in data["reviews"] if item.get("stage") == args.stage]
    entry = {
        "stage": args.stage,
        "version": len(prior) + 1,
        "status": args.status,
        "preview_files": [str(path) for path in previews],
        "note": args.note.strip(),
        "recorded_at": datetime.now(timezone.utc).isoformat(),
    }
    data["reviews"].append(entry)
    review_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Recorded {args.stage} v{entry['version']}: {args.status}")
    print(f"Review state: {review_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
