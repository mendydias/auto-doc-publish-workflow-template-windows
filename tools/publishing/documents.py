"""Discover and normalize documents in the unified sources layout."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*$")
SECTION_NUMBER = re.compile(r"^(\d+)-.+\.md$", re.IGNORECASE)


def discover_documents(root: Path) -> list[str]:
    """Return safe document IDs from the author-facing sources directory."""
    found = {path.parent.name for path in (root / "sources").glob("*/document.yaml")}
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
    """Load a document into one model; unified documents take precedence."""
    if not IDENTIFIER.fullmatch(document):
        raise ValueError(f"Invalid document identifier: {document!r}")
    folder = root / "sources" / document
    if folder.exists() and not folder.resolve().is_relative_to(root.resolve()):
        raise ValueError(f"Document folder escapes repository: {folder}")
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
            section_paths = [_safe_file(folder, str(item[2].relative_to(folder)), "section") for item in sorted(numbered)]
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
            "metadata_file": document_file.resolve(), "resource_base": folder.resolve(),
        }

    raise ValueError(
        f"Document not found in sources/{document}/. Create sources/{document}/document.yaml; "
        "legacy config/documents manifests are no longer supported."
    )
