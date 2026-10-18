"""Manifest and source validation with Pandoc JSON AST parsing."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

try:
    import yaml
except ImportError:  # Allows --help to work before project dependencies are installed.
    yaml = None


def validate(root: Path, manifest_path: Path) -> list[str]:
    if yaml is None:
        return ["PyYAML is missing; create the project environment with .\\scripts\\setup.ps1"]
    errors: list[str] = []
    try:
        manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as error:
        return [f"Invalid manifest: {error}"]
    if not isinstance(manifest, dict):
        return ["Manifest must contain a YAML mapping"]
    if not isinstance(manifest.get("sources"), list) or not manifest["sources"]:
        errors.append("Manifest sources must be a non-empty ordered list")
    output = manifest.get("output", "")
    if not isinstance(output, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", output):
        errors.append("Output basename must be a safe alphanumeric name")
    for rel in [*manifest.get("sources", []), *([manifest["bibliography"]] if manifest.get("bibliography") else [])]:
        path = (root / rel).resolve()
        if not path.is_relative_to(root.resolve()):
            errors.append(f"Path escapes repository: {rel}")
        elif not path.is_file():
            errors.append(f"Missing resource: {rel}")
    return errors


def lint(root: Path) -> int:
    errors = []
    for manifest in sorted((root / "config/documents").glob("*.yaml")):
        for error in validate(root, manifest):
            errors.append(f"{manifest.name}: {error}")
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    print("Manifest lint passed")
    return 0
