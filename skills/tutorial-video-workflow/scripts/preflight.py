#!/usr/bin/env python3
"""Check layered dependencies without installing or modifying the system."""

from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path


def command(name: str) -> dict[str, object]:
    path = shutil.which(name)
    return {"available": path is not None, "path": path}


def browser() -> dict[str, object]:
    for name in ("chromium", "chromium-browser", "google-chrome"):
        path = shutil.which(name)
        if path:
            return {"available": True, "path": path, "kind": name}
    mac_apps = (
        Path("/Applications/Safari.app"),
        Path("/Applications/Google Chrome.app"),
        Path("/Applications/Chromium.app"),
        Path("/Applications/Microsoft Edge.app"),
    )
    found = next((path for path in mac_apps if path.exists()), None)
    return {
        "available": found is not None,
        "path": str(found) if found else None,
        "kind": found.stem if found else None,
    }


def skill(name: str) -> dict[str, object]:
    candidates = [
        Path.home() / ".codex" / "skills" / name,
        Path.home() / ".codex" / "skills" / ".system" / name,
    ]
    found = next((p for p in candidates if (p / "SKILL.md").is_file()), None)
    return {"available": found is not None, "path": str(found) if found else None}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", required=True, type=Path)
    args = parser.parse_args()

    project = args.project.expanduser().resolve()
    report_path = project / "workflow" / "preflight.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)

    report = {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "layers": {
            "base": {
                "python3": command("python3"),
                "ffmpeg": command("ffmpeg"),
                "ffprobe": command("ffprobe"),
                "video-editing-skill": skill("video-editing"),
            },
            "workbench": {"browser": browser()},
        },
    }
    base_ready = all(item["available"] for item in report["layers"]["base"].values())
    workbench_ready = report["layers"]["workbench"]["browser"]["available"]
    report["base_ready"] = base_ready
    report["workbench_ready"] = workbench_ready
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Base workflow: {'ready' if base_ready else 'missing required items'}")
    print(f"Built-in workbench: {'ready' if workbench_ready else 'browser not found'}")
    print(f"Report: {report_path}")
    return 0 if base_ready and workbench_ready else 2


if __name__ == "__main__":
    raise SystemExit(main())
