"""Resolve a document manifest and validate publication configuration."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

from .documents import load_document

IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*$")
SUPPORTED_FORMATS = {"pdf", "latex", "docx", "html", "epub"}
PROFILE_FIELDS = {"id", "documentclass", "classoption", "structure", "top-level-division", "number-sections", "numbersections", "template", "latex-engine", "bibliography", "typography", "formats", "restrictions", "geometry", "fontsize", "mainfont", "mathfont", "linestretch", "fontfamily", "variables", "include-before-body", "include-in-header"}


def _load(path: Path, label: str) -> dict[str, Any]:
    try:
        value = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as error:
        raise ValueError(f"Cannot load {label} {path}: {error}") from error
    if not isinstance(value, dict):
        raise ValueError(f"{label} must contain a YAML mapping: {path}")
    return value


def _config(root: Path, directory: str, name: str, label: str) -> dict[str, Any]:
    if not isinstance(name, str) or not IDENTIFIER.fullmatch(name):
        raise ValueError(f"Invalid {label} identifier: {name!r}")
    path = root / "config" / directory / f"{name}.yaml"
    return _load(path, label)


def resolve_document(
    root: Path,
    document: str,
    profile: str | None = None,
    typography: str | None = None,
    venue: str | None = None,
) -> dict[str, Any]:
    """Resolve explicit CLI values over manifest defaults over project fallbacks."""
    if not IDENTIFIER.fullmatch(document):
        raise ValueError(f"Invalid document identifier: {document!r}")
    author_document = load_document(root, document)
    root = root.resolve()
    def to_relative(paths: list[Path]) -> list[str]:
        return [path.relative_to(root).as_posix() for path in paths]
    raw_metadata = author_document["metadata"]
    if author_document["legacy"]:
        metadata_values = author_document["metadata_values"]
        metadata = raw_metadata.get("metadata", {}) if isinstance(raw_metadata.get("metadata"), dict) else {}
        metadata = {**metadata_values, **metadata}
        title = raw_metadata.get("title", metadata_values.get("title"))
        authors = author_document["authors"]
        date = raw_metadata.get("date", metadata_values.get("date"))
    else:
        metadata = raw_metadata.get("metadata", {})
        if not isinstance(metadata, dict):
            raise ValueError("Document metadata field must be a YAML mapping")
        title = raw_metadata.get("title")
        authors = author_document["authors"]
        date = raw_metadata.get("date")
    if not isinstance(metadata, dict):
        raise ValueError("Document metadata field must be a YAML mapping")
    author_names = [author.get("name", "") if isinstance(author, dict) else author for author in authors] if isinstance(authors, list) else authors
    manifest = {
        "id": document,
        "output": author_document["basename"],
        "profile": author_document["template"],
        "typography": author_document["typography"],
        "venue": author_document["venue"],
        "title": title,
        "authors": authors,
        "author": author_names,
        "date": date,
        "abstract": raw_metadata.get("abstract", metadata.get("abstract", author_document["metadata_values"].get("abstract") if author_document["legacy"] else None)),
        "keywords": raw_metadata.get("keywords", metadata.get("keywords", author_document["metadata_values"].get("keywords") if author_document["legacy"] else None)),
        "metadata": metadata,
        "metadata_file": author_document["metadata_file"].relative_to(root).as_posix() if author_document["metadata_file"] else None,
        "sources": to_relative(author_document["sections"]),
        "bibliography": to_relative(author_document["bibliography"]),
        "assets": to_relative(author_document["assets"]),
        "resource_base": author_document["resource_base"].relative_to(root).as_posix() if author_document["resource_base"] != root else ".",
        "document_folder": author_document["folder"].relative_to(root).as_posix() if author_document["folder"] != root else ".",
        "legacy": author_document["legacy"],
    }
    output = manifest["output"]
    if not isinstance(output, str) or not IDENTIFIER.fullmatch(output):
        raise ValueError("Manifest basename/output must be a safe alphanumeric name")
    selected_profile = profile or manifest.get("profile") or "article"
    selected_venue = venue or manifest.get("venue")
    profile_config = _config(root, "profiles", selected_profile, "profile")
    unknown_profile = set(profile_config) - PROFILE_FIELDS
    if unknown_profile:
        raise ValueError(f"Unknown profile field(s): {', '.join(sorted(unknown_profile))}")
    typography_name = typography or manifest.get("typography") or profile_config.get("typography", {}).get("default") or "default"
    typography_config = _config(root, "typography", typography_name, "typography")
    venue_config = _config(root, "venues", selected_venue, "venue") if selected_venue else {}
    if venue_config:
        allowed_venue = {"id", "illustrative", "paper-size", "page-limit", "anonymous", "submission-checks"}
        unknown_venue = set(venue_config) - allowed_venue
        if unknown_venue:
            raise ValueError("Unknown venue field(s): " + ", ".join(sorted(unknown_venue)))
        if not isinstance(venue_config.get("anonymous", False), bool):
            raise ValueError("Venue anonymous must be a boolean")
        if not isinstance(venue_config.get("page-limit"), int) or venue_config["page-limit"] < 1:
            raise ValueError("Venue page-limit must be a positive integer")
    profile_formats = profile_config.get("formats")
    if profile_formats is not None and (not isinstance(profile_formats, list) or not set(profile_formats) <= SUPPORTED_FORMATS):
        raise ValueError(f"Profile {selected_profile} has invalid supported formats")
    if profile_config.get("typography") is not None and not isinstance(profile_config["typography"], dict):
        raise ValueError("Profile typography settings must be a YAML mapping")
    allowed_typography = profile_config.get("typography", {}).get("allowed")
    if allowed_typography is not None and typography_name not in allowed_typography:
        raise ValueError(
            f"Typography '{typography_name}' is not allowed by profile '{selected_profile}'; "
            f"allowed: {', '.join(allowed_typography)}"
        )
    paths: list[str] = list(manifest["sources"])
    bibliography = manifest.get("bibliography", [])
    if isinstance(bibliography, str):
        bibliography = [bibliography]
    if not isinstance(bibliography, list):
        raise ValueError("Manifest bibliography must be a path or ordered list of paths")
    paths.extend(bibliography)
    paths.extend(manifest["assets"])
    if manifest.get("metadata_file"):
        paths.append(manifest["metadata_file"])
    for rel in paths:
        if not isinstance(rel, str):
            raise ValueError(f"Manifest paths must be strings: {rel!r}")
        candidate = (root / rel).resolve()
        if not candidate.is_relative_to(root):
            raise ValueError(f"Path escapes repository: {rel}")
        if not candidate.is_file():
            raise ValueError(f"Missing resource: {rel}")
    for rel in (profile_config.get("template"), profile_config.get("bibliography", {}).get("style")):
        if rel:
            candidate = (root / rel).resolve()
            if not candidate.is_relative_to(root) or not candidate.is_file():
                raise ValueError(f"Missing or unsafe profile resource: {rel}")
    if profile_config.get("latex-engine", "lualatex") not in {"pdflatex", "lualatex", "xelatex"}:
        raise ValueError("Unsupported LaTeX engine in profile")
    processor = profile_config.get("bibliography", {}).get("processor", "citeproc")
    if processor not in {"citeproc", "bibtex", "biber"}:
        raise ValueError("Unsupported bibliography processor in profile")
    if selected_profile == "ieee-conference":
        ieee_metadata = {**manifest["metadata"], **{key: manifest.get(key) for key in ("title", "authors", "abstract", "keywords") if manifest.get(key) is not None}}
        if not isinstance(ieee_metadata.get("title"), str) or not ieee_metadata["title"].strip():
            raise ValueError("IEEE metadata requires a non-empty title")
        if not isinstance(ieee_metadata.get("authors"), list) or not ieee_metadata["authors"]:
            raise ValueError("IEEE metadata requires a non-empty authors list")
        for index, author in enumerate(ieee_metadata["authors"], 1):
            if not isinstance(author, dict) or not all(isinstance(author.get(field), str) and author[field].strip() for field in ("name", "affiliation")):
                raise ValueError(f"IEEE author {index} requires name and affiliation strings")
        if not isinstance(ieee_metadata.get("abstract"), str) or not ieee_metadata["abstract"].strip():
            raise ValueError("IEEE metadata requires a non-empty abstract")
        if not isinstance(ieee_metadata.get("keywords"), list) or not ieee_metadata["keywords"]:
            raise ValueError("IEEE metadata requires a non-empty keywords list")
    return {
        "document": document,
        "manifest": manifest,
        "profile": selected_profile,
        "profile_config": profile_config,
        "typography": typography_name,
        "typography_config": typography_config,
        "venue": selected_venue,
        "venue_config": venue_config,
        "output": output,
    }
