"""Debounced polling watcher; ignores generated output and serializes builds."""

from __future__ import annotations

import time
from pathlib import Path

from .build import build


def watched_files(root: Path, document: str | None = None) -> list[Path]:
    """Return author inputs and shared renderer configuration, excluding outputs."""
    inputs = [root / "templates", root / "config"]
    if document is None:
        inputs.append(root / "sources")
    else:
        inputs.append(root / "sources" / document)
    paths: set[Path] = set()
    for directory in inputs:
        if directory.exists():
            paths.update(path for path in directory.rglob("*") if path.is_file())
    return sorted(paths)


def _snapshot(root: Path, document: str | None = None) -> dict[Path, tuple[int, int]]:
    return {path: (path.stat().st_mtime_ns, path.stat().st_size) for path in watched_files(root, document)}


def wait_for_quiet(root: Path, document: str | None, state: dict[Path, tuple[int, int]], quiet_period: float = 0.6) -> dict[Path, tuple[int, int]]:
    """Wait until changes stop for a full debounce interval, updating the snapshot."""
    quiet_until = time.monotonic() + quiet_period
    while True:
        time.sleep(0.1)
        refreshed = _snapshot(root, document)
        if refreshed != state:
            state = refreshed
            quiet_until = time.monotonic() + quiet_period
        if time.monotonic() >= quiet_until:
            return state


def watch(root: Path, document: str, profile: str | None, typography: str | None, format_name: str, venue: str | None = None) -> int:
    state = _snapshot(root, document)
    print(f"Watching sources/{document} and shared renderer configuration (Ctrl+C to stop)")
    try:
        while True:
            time.sleep(0.4)
            changed = False
            current = _snapshot(root, document)
            changed = current != state
            state = current
            if changed:
                state = wait_for_quiet(root, document, state)
                print("Change detected; rebuilding")
                try:
                    result = build(root, document, profile, typography, format_name, venue)
                except (ValueError, OSError, RuntimeError) as error:
                    print(f"Rebuild failed: {error}")
                else:
                    if result:
                        print(f"Rebuild failed with exit code {result}")
    except KeyboardInterrupt:
        print("Watch stopped")
        return 0
