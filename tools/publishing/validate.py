"""Manifest and source validation with Pandoc JSON AST parsing."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

try:
    import yaml
except ImportError:  # Allows --help to work before project dependencies are installed.
    yaml = None


def validate(root: Path, manifest_path: Path | dict, source_overrides: list[str] | None = None) -> list[str]:
    if yaml is None:
        return ["PyYAML is missing; create the project environment with .\\scripts\\setup.ps1"]
    errors: list[str] = []
    if isinstance(manifest_path, dict):
        manifest = dict(manifest_path)
    else:
        try:
            manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError) as error:
            return [f"Invalid manifest: {error}"]
        if not isinstance(manifest, dict):
            return ["Manifest must contain a YAML mapping"]
        if isinstance(manifest.get("metadata"), str):
            manifest = {**manifest, "metadata_file": manifest["metadata"], "metadata": {}}
    if source_overrides is not None:
        manifest = {**manifest, "sources": source_overrides}
    if not isinstance(manifest.get("sources"), list) or not manifest["sources"]:
        errors.append("Manifest sources must be a non-empty ordered list")
    external_metadata = {}
    if isinstance(manifest.get("metadata_file"), str):
        metadata_path = (root / manifest["metadata_file"]).resolve()
        if not metadata_path.is_relative_to(root.resolve()) or not metadata_path.is_file():
            errors.append(f"Missing or unsafe metadata file: {manifest['metadata_file']}")
        else:
            try:
                external_metadata = yaml.safe_load(metadata_path.read_text(encoding="utf-8")) or {}
            except yaml.YAMLError as error:
                errors.append(f"Invalid metadata YAML: {error}")
            if not isinstance(external_metadata, dict):
                errors.append(f"Metadata file must contain a YAML mapping: {manifest['metadata_file']}")
                external_metadata = {}
    metadata_values = manifest.get("metadata", {}) if isinstance(manifest.get("metadata"), dict) else {}
    title = manifest.get("title", metadata_values.get("title", external_metadata.get("title")))
    authors = manifest.get("authors", manifest.get("author", metadata_values.get("authors", external_metadata.get("authors", external_metadata.get("author")))))
    if not isinstance(title, str) or not title.strip():
        errors.append("Manifest requires a non-empty title")
    if not isinstance(authors, (str, list)) or not authors:
        errors.append("Manifest requires an author string or ordered author list")
    if not isinstance(manifest.get("metadata", {}), (dict, str)):
        errors.append("Manifest metadata must be a YAML mapping")
    output = manifest.get("basename", manifest.get("output", ""))
    if not isinstance(output, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", output):
        errors.append("Output basename must be a safe alphanumeric name")
    bibliography = manifest.get("bibliography", [])
    bibliography = [bibliography] if isinstance(bibliography, str) else bibliography
    if not isinstance(bibliography, list):
        errors.append("Manifest bibliography must be a path or list of paths")
        bibliography = []
    for rel in [*manifest.get("sources", []), *bibliography, *manifest.get("assets", []), *([manifest["metadata_file"]] if isinstance(manifest.get("metadata_file"), str) else [])]:
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
        [shutil.which("pandoc") or "pandoc", *map(str, source_paths), "--from", "markdown+tex_math_dollars+raw_tex+fenced_divs+bracketed_spans", "--to", "json", "--resource-path", _resource_path(root, manifest)],
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
            content = node.get("c")
            attr_index = {"Header": 1, "Figure": 0, "Table": 0, "CodeBlock": 0, "Div": 0, "Span": 0, "Image": 0}.get(node.get("t"))
            if attr_index is not None and isinstance(content, list) and len(content) > attr_index:
                attr = content[attr_index]
                if isinstance(attr, list) and len(attr) == 3 and isinstance(attr[0], str) and attr[0]:
                    identifiers.append(attr[0])
            # Pandoc represents the equation label suffix as a Str adjacent to a Math
            # block (rather than an Attr); inspect that parsed AST context, not raw MD.
            if node.get("t") == "Para" and isinstance(content, list):
                if any(isinstance(child, dict) and child.get("t") == "Math" and child.get("c", [{}])[0].get("t") == "DisplayMath" for child in content):
                    for child in content:
                        if isinstance(child, dict) and child.get("t") == "Str":
                            text = child.get("c", "")
                            if isinstance(text, str) and text.startswith("{#eq:") and text.endswith("}"):
                                identifiers.append(text[2:-1])
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
        candidates = _resource_candidates(root, manifest, source_paths, target)
        resource = next((candidate for candidate in candidates if candidate.is_file()), None)
        allowed = []
        resource_base = manifest.get("resource_base")
        if isinstance(resource_base, str):
            allowed.append((root / resource_base).resolve())
        allowed.extend(source.resolve().parent for source in source_paths)
        if resource is None or not any(resource.is_relative_to(base) for base in allowed):
            errors.append(f"Missing or unsafe resource: {target}")
    if bibliography:
        try:
            import bibtexparser
            keys = []
            for bibliography_path in bibliography:
                with (root / bibliography_path).open(encoding="utf-8") as bib_file:
                    db = bibtexparser.load(bib_file)
                keys.extend(entry["ID"] for entry in db.entries)
            errors.extend(f"Duplicate bibliography key: {key}" for key in sorted({key for key in keys if keys.count(key) > 1}))
            available = set(keys)
            missing = sorted(set(citations) - label_references - available)
            errors.extend(f"Missing citation key: {key}" for key in missing)
        except (ImportError, OSError, ValueError) as error:
            errors.append(f"Could not parse bibliography: {error}")
    return errors


def _resource_candidates(root: Path, manifest: dict, sources: list[Path], target: str) -> list[Path]:
    path = Path(target)
    if path.is_absolute():
        return [path.resolve()]
    candidates = [source.parent / path for source in sources]
    base = manifest.get("resource_base")
    if isinstance(base, str):
        candidates.append(root / base / path)
    candidates.append(root / path)
    return [candidate.resolve() for candidate in candidates]


def _resource_path(root: Path, manifest: dict) -> str:
    bases = [root.resolve()]
    base = manifest.get("resource_base")
    if isinstance(base, str):
        bases.append((root / base).resolve())
    bases.extend((root / source).resolve().parent for source in manifest.get("sources", []))
    return os.pathsep.join(dict.fromkeys(map(str, bases)))


def lint(root: Path) -> int:
    from .documents import discover_documents
    from .resolve_document import resolve_document

    errors = []
    for document in discover_documents(root):
        try:
            resolved = resolve_document(root, document)
        except (ValueError, OSError) as error:
            errors.append(f"{document}: {error}")
            continue
        for error in validate(root, resolved["manifest"]):
            errors.append(f"{document}: {error}")
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    ruff = shutil.which("ruff")
    if not ruff:
        local_ruff = Path(sys.executable).parent / ("ruff.exe" if sys.platform == "win32" else "ruff")
        if local_ruff.is_file():
            ruff = str(local_ruff)
    if ruff:
        result = subprocess.run([ruff, "check", str(root / "tools"), str(root / "tests")], cwd=root, check=False)
        if result.returncode:
            return result.returncode
    else:
        print("Ruff is missing; install pinned project dev dependencies with scripts/setup.ps1", file=sys.stderr)
        return 2
    markdownlint = shutil.which("pymarkdown")
    if not markdownlint:
        local = Path(sys.executable).parent / ("pymarkdown.exe" if sys.platform == "win32" else "pymarkdown")
        if local.is_file():
            markdownlint = str(local)
    if markdownlint:
        sources = [str(path) for path in sorted((root / "sources").rglob("*.md"))]
        result = subprocess.run([markdownlint, "--config", str(root / ".pymarkdown.json"), "scan", *sources], cwd=root, check=False)
        if result.returncode:
            return result.returncode
    else:
        print("Markdown lint unavailable: install the pinned project dev dependencies with scripts/setup.ps1", file=sys.stderr)
        return 2
    print("Manifest lint passed")
    return 0
