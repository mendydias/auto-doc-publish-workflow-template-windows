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
        if not isinstance(rel, str):
            errors.append(f"Manifest path must be a string: {rel!r}")
            continue
        path = (root / rel).resolve()
        if not path.is_relative_to(root.resolve()):
            errors.append(f"Path escapes repository: {rel}")
        elif not path.is_file():
            errors.append(f"Missing resource: {rel}")
    if errors:
        return errors
    if not shutil.which("pandoc"):
        return ["Pandoc is required for AST validation"]
    source_paths = [root / rel for rel in manifest["sources"]]
    ast_process = subprocess.run(
        [shutil.which("pandoc") or "pandoc", *map(str, source_paths), "--from", "markdown+tex_math_dollars+raw_tex+fenced_divs+bracketed_spans", "--to", "json", "--resource-path", str(root)],
        cwd=root, capture_output=True, text=True, check=False,
    )
    if ast_process.returncode:
        return [f"Pandoc could not parse sources: {ast_process.stderr.strip()}"]
    try:
        document = json.loads(ast_process.stdout)
    except json.JSONDecodeError as error:
        return [f"Pandoc returned invalid JSON AST: {error}"]
    identifiers: list[str] = []
    citations: list[str] = []
    resources: list[str] = []

    def visit(node: object) -> None:
        if isinstance(node, dict):
            if node.get("t") == "Cite":
                citations.extend(item.get("citationId", "") for item in node.get("c", [[]])[0])
            if node.get("t") in ("Image", "Link"):
                content = node.get("c", [])
                if len(content) >= 3 and isinstance(content[2], list) and content[2]:
                    resources.append(content[2][0])
            attr = node.get("c")
            if isinstance(attr, list) and attr and isinstance(attr[0], list) and len(attr[0]) >= 1 and isinstance(attr[0][0], str):
                if attr[0][0]:
                    identifiers.append(attr[0][0])
            for value in node.values():
                visit(value)
        elif isinstance(node, list):
            for value in node:
                visit(value)

    visit(document)
    duplicate_labels = sorted({label for label in identifiers if identifiers.count(label) > 1})
    errors.extend(f"Duplicate label: {label}" for label in duplicate_labels)
    label_references = {key for key in citations if key.startswith(("fig:", "tbl:", "eq:", "sec:", "lst:"))}
    errors.extend(f"Unresolved cross-reference: {key}" for key in sorted(label_references - set(identifiers)))
    for target in resources:
        if not target or re.match(r"^(?:https?:|data:|#)", target, re.I):
            continue
        resource = (root / target).resolve()
        if not resource.is_relative_to(root.resolve()) or not resource.is_file():
            errors.append(f"Missing or unsafe resource: {target}")
    bibliography = manifest.get("bibliography")
    if bibliography:
        try:
            import bibtexparser
            with (root / bibliography).open(encoding="utf-8") as bib_file:
                db = bibtexparser.load(bib_file)
            keys = [entry["ID"] for entry in db.entries]
            errors.extend(f"Duplicate bibliography key: {key}" for key in sorted({key for key in keys if keys.count(key) > 1}))
            available = set(keys)
            missing = sorted(set(citations) - label_references - available)
            errors.extend(f"Missing citation key: {key}" for key in missing)
        except (ImportError, OSError, ValueError) as error:
            errors.append(f"Could not parse bibliography: {error}")
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
