#!/bin/sh
# Bootstrap the workflow without assuming Python is already installed.

set -u

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)

find_python() {
  if command -v python3 >/dev/null 2>&1; then
    command -v python3
    return 0
  fi
  if command -v python >/dev/null 2>&1 && python -c 'import sys; raise SystemExit(0 if sys.version_info.major == 3 else 1)' >/dev/null 2>&1; then
    command -v python
    return 0
  fi
  return 1
}

print_install_hint() {
  os_name=$(uname -s 2>/dev/null || printf 'unknown')
  printf '%s\n' 'Python 3 is required but was not found.'
  printf 'Detected system: %s\n' "$os_name"
  case "$os_name" in
    Darwin)
      if command -v brew >/dev/null 2>&1; then
        printf '%s\n' 'Recommended installer: existing Homebrew (python package).'
      else
        printf '%s\n' 'Recommended installer: official Python for macOS, or Homebrew after separate approval.'
      fi
      ;;
    Linux)
      for manager in apt-get dnf yum pacman zypper; do
        if command -v "$manager" >/dev/null 2>&1; then
          printf 'Recommended installer: system package manager %s.\n' "$manager"
          break
        fi
      done
      ;;
    *)
      printf '%s\n' 'Use the operating system supported Python 3 installer.'
      ;;
  esac
  printf '%s\n' 'Codex must explain the change and obtain approval before installing.'
}

PYTHON_BIN=$(find_python) || {
  print_install_hint
  exit 2
}

printf 'Python 3 found: %s\n' "$PYTHON_BIN"
"$PYTHON_BIN" --version
exec "$PYTHON_BIN" "$SCRIPT_DIR/preflight.py" "$@"
