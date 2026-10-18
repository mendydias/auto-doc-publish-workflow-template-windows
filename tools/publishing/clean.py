"""Conservative cleanup limited to the repository build directory."""

from __future__ import annotations

import shutil
import os
from pathlib import Path


def clean(root: Path) -> int:
    target = root / "build"
    resolved_root = root.resolve()
    resolved_target = target.resolve(strict=False)
    is_junction = getattr(target, "is_junction", lambda: False)()
    if target.is_symlink() or is_junction or not resolved_target.is_relative_to(resolved_root) or resolved_target == resolved_root:
        raise ValueError(f"Refusing unsafe cleanup target: {target}")
    # Preflight the complete tree before deleting anything; junctions are not always
    # reported as symlinks on Windows. Refuse rather than risk escaping build/.
    for current, directories, files in os.walk(target, followlinks=False):
        for name in [*directories, *files]:
            entry = Path(current) / name
            if entry.is_symlink() or getattr(entry, "is_junction", lambda: False)():
                raise ValueError(f"Refusing cleanup because build contains a link/junction: {entry}")
    for child in target.iterdir():
        if child.name == ".gitkeep":
            continue
        if child.is_symlink():
            raise ValueError(f"Refusing to traverse symlink during cleanup: {child}")
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()
    print(f"Cleaned generated contents of {target}")
    return 0
