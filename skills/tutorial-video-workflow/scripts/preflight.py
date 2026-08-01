#!/usr/bin/env python3
"""Check layered dependencies without installing or modifying the system."""

from __future__ import annotations

import argparse
import json
import shutil
import urllib.error
import urllib.request
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
        Path("/Applications/Google Chrome.app"),
        Path("/Applications/Chromium.app"),
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


def openchatcut(url: str) -> dict[str, object]:
    try:
        with urllib.request.urlopen(url, timeout=0.8) as response:
            return {"available": True, "status": response.status, "url": url}
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return {"available": False, "url": url, "detail": str(exc)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", required=True, type=Path)
    parser.add_argument("--openchatcut-url", default="http://localhost:5199/api/external-mcp/mcp")
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
            "visual_optional": {
                "node": command("node"),
                "npm": command("npm"),
                "chromium-compatible-browser": browser(),
                "design-style-skill": skill("design-style"),
                "imagegen-skill": skill("imagegen"),
            },
            "openchatcut_optional": openchatcut(args.openchatcut_url),
        },
    }
    base_ready = all(item["available"] for item in report["layers"]["base"].values())
    report["base_ready"] = base_ready
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Base workflow: {'ready' if base_ready else 'missing required items'}")
    print(f"Report: {report_path}")
    return 0 if base_ready else 2


if __name__ == "__main__":
    raise SystemExit(main())
