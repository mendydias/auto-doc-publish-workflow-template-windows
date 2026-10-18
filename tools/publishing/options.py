"""Resolve shared command-line and environment publishing options."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class PublishOptions:
    document: str = "example"
    template: str | None = None
    format: str = "pdf"
    action: str = "Build"
    non_interactive: bool = False
    typography: str | None = None
    venue: str | None = None


def resolve_options(args: object, environ: dict[str, str] | None = None) -> PublishOptions:
    """CLI values take precedence over validated PUBLISH_* values."""
    env = os.environ if environ is None else environ

    def choose(attribute: str, variable: str, default: str | None = None) -> str | None:
        cli = getattr(args, attribute, None)
        value = cli if cli is not None else env.get(variable)
        return value if value is not None else default

    alias = getattr(args, "profile", None)
    template = getattr(args, "template", None)
    env_template = env.get("PUBLISH_TEMPLATE")
    if alias and template and alias != template:
        raise ValueError("--profile and --template conflict; use one template selection")
    if alias and env_template and alias != env_template and template is None:
        raise ValueError("--profile conflicts with PUBLISH_TEMPLATE")
    selected_template = template or alias or env_template
    action = choose("action", "PUBLISH_ACTION", "Build")
    format_name = choose("format", "PUBLISH_FORMAT", "pdf")
    document = choose("document", "PUBLISH_DOCUMENT", "example")
    typography = choose("typography", "PUBLISH_TYPOGRAPHY")
    venue = choose("venue", "PUBLISH_VENUE")
    non_interactive_cli = getattr(args, "non_interactive", None)
    non_interactive = non_interactive_cli if non_interactive_cli is not None else env.get("PUBLISH_NON_INTERACTIVE", "").lower() in {"1", "true", "yes", "on"}

    actions = {"Check", "Build", "Lint", "Validate", "Package", "Test", "Watch", "Clean", "Handoff"}
    formats = {"pdf", "latex", "docx", "html", "epub", "all"}
    if action not in actions:
        raise ValueError(f"Invalid publishing action: {action!r}")
    if format_name not in formats:
        raise ValueError(f"Invalid publishing format: {format_name!r}")
    for label, value in (("document", document), ("template", selected_template), ("typography", typography), ("venue", venue)):
        if value is not None and (not value or any(char not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-" for char in value) or value[0] not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"):
            raise ValueError(f"Invalid {label} identifier: {value!r}")
    return PublishOptions(document, selected_template, format_name, action, bool(non_interactive), typography, venue)
