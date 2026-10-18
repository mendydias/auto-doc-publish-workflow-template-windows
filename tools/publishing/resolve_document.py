"""Resolve a document manifest and validate publication configuration."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*$")
SUPPORTED_FORMATS = {"pdf", "latex", "docx", "html", "epub"}
MANIFEST_FIELDS = {"id", "basename", "output", "profile", "venue", "metadata", "bibliography", "sources", "title", "author", "date"}
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
    manifest_path = root / "config/documents" / f"{document}.yaml"
    if not IDENTIFIER.fullmatch(document) or not manifest_path.is_file():
        raise ValueError(f"Document manifest not found or unsafe: {document}")
    manifest = _load(manifest_path, "document manifest")
    unknown_manifest = set(manifest) - MANIFEST_FIELDS
    if unknown_manifest:
        raise ValueError("Unknown document manifest field(s): " + ", ".join(sorted(unknown_manifest)))
    if "sources" not in manifest or not isinstance(manifest["sources"], list) or not manifest["sources"]:
        raise ValueError("Manifest sources must be a non-empty ordered list")
    output = manifest.get("basename", manifest.get("output"))
    if not isinstance(output, str) or not IDENTIFIER.fullmatch(output):
        raise ValueError("Manifest basename/output must be a safe alphanumeric name")
    selected_profile = profile or manifest.get("profile") or "article"
    selected_venue = venue or manifest.get("venue")
    profile_config = _config(root, "profiles", selected_profile, "profile")
    unknown_profile = set(profile_config) - PROFILE_FIELDS
    if unknown_profile:
        raise ValueError(f"Unknown profile field(s): {', '.join(sorted(unknown_profile))}")
    typography_name = typography or profile_config.get("typography", {}).get("default") or "default"
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
    if isinstance(manifest.get("metadata"), str):
        paths.append(manifest["metadata"])
    elif manifest.get("metadata") is not None and not isinstance(manifest["metadata"], dict):
        raise ValueError("Manifest metadata must be a path or YAML mapping")
    for rel in paths:
        if not isinstance(rel, str):
            raise ValueError(f"Manifest paths must be strings: {rel!r}")
        candidate = (root / rel).resolve()
        if not candidate.is_relative_to(root.resolve()):
            raise ValueError(f"Path escapes repository: {rel}")
        if not candidate.is_file():
            raise ValueError(f"Missing resource: {rel}")
    for rel in (profile_config.get("template"), profile_config.get("bibliography", {}).get("style")):
        if rel:
            candidate = (root / rel).resolve()
            if not candidate.is_relative_to(root.resolve()) or not candidate.is_file():
                raise ValueError(f"Missing or unsafe profile resource: {rel}")
    if profile_config.get("latex-engine", "lualatex") not in {"pdflatex", "lualatex", "xelatex"}:
        raise ValueError("Unsupported LaTeX engine in profile")
    processor = profile_config.get("bibliography", {}).get("processor", "citeproc")
    if processor not in {"citeproc", "bibtex", "biber"}:
        raise ValueError("Unsupported bibliography processor in profile")
    if selected_profile == "ieee-conference":
        if not isinstance(manifest.get("metadata"), str):
            raise ValueError("IEEE document manifest metadata must be a repository-relative YAML path")
        metadata_path = root / manifest["metadata"]
        metadata = _load(metadata_path, "IEEE metadata")
        authors = metadata.get("authors")
        if not isinstance(metadata.get("title"), str) or not metadata["title"].strip():
            raise ValueError("IEEE metadata requires a non-empty title")
        if not isinstance(authors, list) or not authors:
            raise ValueError("IEEE metadata requires a non-empty authors list")
        for index, author in enumerate(authors, 1):
            if not isinstance(author, dict) or not all(isinstance(author.get(field), str) and author[field].strip() for field in ("name", "affiliation")):
                raise ValueError(f"IEEE author {index} requires name and affiliation strings")
        if not isinstance(metadata.get("abstract"), str) or not metadata["abstract"].strip():
            raise ValueError("IEEE metadata requires a non-empty abstract")
        if not isinstance(metadata.get("keywords"), list) or not metadata["keywords"]:
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
