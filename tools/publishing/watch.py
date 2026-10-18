"""Debounced polling watcher; ignores generated output and serializes builds."""

from __future__ import annotations

import time
from pathlib import Path

from .build import build


def watch(root: Path, document: str, profile: str, typography: str, format_name: str) -> int:
    manifest = root / "config/documents" / f"{document}.yaml"
    sources = [root / "sources"]
    paths = [manifest, *[p for base in sources for p in base.rglob("*") if p.is_file()]]
    state = {path: path.stat().st_mtime_ns for path in paths}
    print("Watching sources (Ctrl+C to stop)")
    try:
        while True:
            time.sleep(0.4)
            changed = False
            current = [manifest, *[p for base in sources for p in base.rglob("*") if p.is_file()]]
            for path in current:
                stamp = path.stat().st_mtime_ns
                if state.get(path) != stamp:
                    changed = True
                state[path] = stamp
            if changed:
                time.sleep(0.6)
                print("Change detected; rebuilding")
                build(root, document, profile, typography, format_name)
    except KeyboardInterrupt:
        print("Watch stopped")
        return 0
