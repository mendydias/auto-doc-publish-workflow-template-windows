"""Conservative cleanup limited to the repository build directory."""

from __future__ import annotations

import shutil
from pathlib import Path


def clean(root: Path) -> int:
    target = root / "build"
    resolved_root = root.resolve()
    resolved_target = target.resolve(strict=False)
    if target.is_symlink() or not resolved_target.is_relative_to(resolved_root) or resolved_target == resolved_root:
        raise ValueError(f"Refusing unsafe cleanup target: {target}")
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
