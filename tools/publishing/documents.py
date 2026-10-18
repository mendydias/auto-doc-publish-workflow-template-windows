"""Discover and normalize documents in the unified sources layout.

Legacy config/documents manifests are exposed through the same normalized
shape while the repository migrates its examples.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*$")
SECTION_NUMBER = re.compile(r"^(\d+)-.+\.md$", re.IGNORECASE)


def discover_documents(root: Path) -> list[str]:
    """Return safe document IDs from new and legacy document locations."""
    found = {path.parent.name for path in (root / "sources").glob("*/document.yaml")}
    found.update(path.stem for path in (root / "config/documents").glob("*.yaml"))
    return sorted(name for name in found if IDENTIFIER.fullmatch(name))


def _safe_file(folder: Path, relative: str, label: str) -> Path:
    if not isinstance(relative, str) or not relative or Path(relative).is_absolute():
        raise ValueError(f"{label} must be a non-empty relative path: {relative!r}")
    candidate = (folder / relative).resolve()
    if not candidate.is_relative_to(folder.resolve()):
        raise ValueError(f"{label} escapes document folder: {relative}")
    if not candidate.is_file():
        raise ValueError(f"Missing {label}: {relative}")
    return candidate


def _yaml_mapping(path: Path, label: str) -> dict[str, Any]:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as error:
        raise ValueError(f"Cannot load {label} {path}: {error}") from error
    if not isinstance(data, dict):
        raise ValueError(f"{label} must be a YAML mapping: {path}")
    return data


def load_document(root: Path, document: str) -> dict[str, Any]:
    """Load a document into a common model with resolved source/resource paths."""
    if not IDENTIFIER.fullmatch(document):
        raise ValueError(f"Invalid document identifier: {document!r}")
    folder = root / "sources" / document
    document_file = folder / "document.yaml"
    if document_file.is_file():
        metadata = _yaml_mapping(document_file, "document metadata")
        allowed = {"title", "authors", "author", "date", "abstract", "keywords", "sections",
                   "bibliography", "assets", "template", "profile", "typography", "venue",
                   "basename", "output", "metadata", "frontmatter"}
        unknown = set(metadata) - allowed
        if unknown:
            raise ValueError("Unknown document field(s): " + ", ".join(sorted(unknown)))
        section_paths: list[Path]
        explicit = metadata.get("sections")
        if explicit is None:
            directory = folder / "sections"
            numbered = []
            if directory.is_dir():
                for path in directory.glob("*.md"):
                    match = SECTION_NUMBER.fullmatch(path.name)
                    if not match:
                        raise ValueError(f"Section filename must start with a number and hyphen: {path}")
                    numbered.append((int(match.group(1)), path.name, path))
            numbers = [item[0] for item in numbered]
            duplicates = sorted({number for number in numbers if numbers.count(number) > 1})
            if duplicates:
                raise ValueError("Duplicate section number(s): " + ", ".join(map(str, duplicates)))
            section_paths = [item[2].resolve() for item in sorted(numbered)]
        else:
            if not isinstance(explicit, list) or not explicit:
                raise ValueError("sections must be a non-empty ordered list")
            section_paths = [_safe_file(folder, entry, "section") for entry in explicit]
        if not section_paths:
            raise ValueError(f"Document {document!r} has no Markdown sections")
        authors = metadata.get("authors", metadata.get("author"))
        if isinstance(authors, str):
            authors = [{"name": authors}]
        if not isinstance(authors, list) or not authors or any(
            not isinstance(author, dict) or not isinstance(author.get("name"), str) or not author["name"].strip()
            for author in authors
        ):
            raise ValueError("authors must be a non-empty list of mappings with a name")
        bibliography = metadata.get("bibliography", [])
        if isinstance(bibliography, str):
            bibliography = [bibliography]
        if not isinstance(bibliography, list):
            raise ValueError("bibliography must be a path or ordered list of paths")
        bibliography_paths = [_safe_file(folder, item, "bibliography") for item in bibliography]
        assets = metadata.get("assets", [])
        if not isinstance(assets, list):
            raise ValueError("assets must be an ordered list of relative paths")
        asset_paths = [_safe_file(folder, item, "asset") for item in assets]
        return {
            "id": document, "folder": folder.resolve(), "metadata": metadata,
            "authors": authors, "sections": section_paths, "bibliography": bibliography_paths,
            "assets": asset_paths, "template": metadata.get("template", metadata.get("profile")),
            "typography": metadata.get("typography"), "venue": metadata.get("venue"),
            "basename": metadata.get("basename", metadata.get("output", document)), "legacy": False,
        }

    manifest_path = root / "config/documents" / f"{document}.yaml"
    if not manifest_path.is_file():
        raise ValueError(f"Document not found: {document}")
    manifest = _yaml_mapping(manifest_path, "legacy document manifest")
    sources = manifest.get("sources")
    if not isinstance(sources, list) or not sources:
        raise ValueError("Legacy manifest sources must be a non-empty ordered list")
    paths = [_safe_file(root, item, "source") for item in sources]
    bibliography = manifest.get("bibliography", [])
    if isinstance(bibliography, str):
        bibliography = [bibliography]
    if not isinstance(bibliography, list):
        raise ValueError("Legacy bibliography must be a path or ordered list")
    bib_paths = [_safe_file(root, item, "bibliography") for item in bibliography]
    return {
        "id": document, "folder": root.resolve(), "metadata": manifest,
        "authors": manifest.get("authors", manifest.get("author", [])), "sections": paths,
        "bibliography": bib_paths, "assets": [],
        "template": manifest.get("template", manifest.get("profile")),
        "typography": manifest.get("typography"), "venue": manifest.get("venue"),
        "basename": manifest.get("basename", manifest.get("output", document)), "legacy": True,
    }
