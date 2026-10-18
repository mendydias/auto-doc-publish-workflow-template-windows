"""Debounced polling watcher; ignores generated output and serializes builds."""

from __future__ import annotations

import time
from pathlib import Path

from .build import build


def watched_files(root: Path, manifest: Path) -> list[Path]:
    """Return tracked project inputs; build/cache paths are deliberately excluded."""
    inputs = [root / "sources", root / "references", root / "assets", root / "templates", root / "config"]
    paths = {manifest}
    for directory in inputs:
        if directory.exists():
            paths.update(path for path in directory.rglob("*") if path.is_file())
    return sorted(paths)


def _snapshot(root: Path, manifest: Path) -> dict[Path, int]:
    return {path: path.stat().st_mtime_ns for path in watched_files(root, manifest)}


def wait_for_quiet(root: Path, manifest: Path, state: dict[Path, int], quiet_period: float = 0.6) -> dict[Path, int]:
    """Wait until changes stop for a full debounce interval, updating the snapshot."""
    quiet_until = time.monotonic() + quiet_period
    while True:
        time.sleep(0.1)
        refreshed = _snapshot(root, manifest)
        if refreshed != state:
            state = refreshed
            quiet_until = time.monotonic() + quiet_period
        if time.monotonic() >= quiet_until:
            return state


def watch(root: Path, document: str, profile: str, typography: str, format_name: str, venue: str | None = None) -> int:
    manifest = root / "config/documents" / f"{document}.yaml"
    state = _snapshot(root, manifest)
    print("Watching sources (Ctrl+C to stop)")
    try:
        while True:
            time.sleep(0.4)
            changed = False
            current = _snapshot(root, manifest)
            changed = current != state
            state = current
            if changed:
                state = wait_for_quiet(root, manifest, state)
                print("Change detected; rebuilding")
                build(root, document, profile, typography, format_name, venue)
    except KeyboardInterrupt:
        print("Watch stopped")
        return 0
