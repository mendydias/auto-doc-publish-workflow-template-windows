"""CLI entry point; all paths are rooted at the repository, never the caller's cwd."""

from __future__ import annotations

import argparse
import os
import sys
from dataclasses import replace
from pathlib import Path

from .build import build
from .clean import clean
from .dependencies import check_dependencies
from .validate import lint
from .watch import watch
from .handoff import generate as generate_handoff
from .submission import check_venue, package
from .options import resolve_options
from .documents import discover_documents, load_document

ROOT = Path(__file__).resolve().parents[2]


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description="Build and validate academic Markdown publications.")
    result.add_argument("--action", choices=["Check", "Build", "Lint", "Validate", "Package", "Test", "Watch", "Clean", "Handoff"], default=None)
    result.add_argument("--document", default=None)
    result.add_argument("--template", default=None, help="Publishing template")
    result.add_argument("--profile", default=None, help="Compatibility alias for --template")
    result.add_argument("--typography", default=None, help="Typography preset")
    result.add_argument("--venue", default=None, help="Venue rules")
    result.add_argument("--format", dest="format", choices=["pdf", "latex", "docx", "html", "epub", "all"], default=None)
    result.add_argument("--non-interactive", action="store_true", default=None)
    return result


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        options = resolve_options(args)
        unattended = options.non_interactive or bool(os.environ.get("CI")) or not sys.stdin.isatty()
        if options.action == "Build":
            document_selected = args.document is not None or "PUBLISH_DOCUMENT" in os.environ
            if not document_selected:
                documents = discover_documents(ROOT)
                if len(documents) == 1:
                    options = replace(options, document=documents[0])
                elif unattended:
                    raise ValueError("Select a document with --document or PUBLISH_DOCUMENT in unattended mode")
                else:
                    options = replace(options, document=_menu("Select a document", documents))
            template_selected = args.template is not None or args.profile is not None or "PUBLISH_TEMPLATE" in os.environ
            if not template_selected:
                model = load_document(ROOT, options.document)
                default_template = model.get("template")
                choices = sorted(path.stem for path in (ROOT / "config/profiles").glob("*.yaml"))
                if unattended:
                    if default_template:
                        options = replace(options, template=default_template)
                    else:
                        raise ValueError("Select a template with --template or PUBLISH_TEMPLATE in unattended mode")
                else:
                    options = replace(options, template=_menu("Select a template", choices, default_template))
        if options.action == "Check":
            return check_dependencies(ROOT, options.format)
        if options.action == "Build":
            return build(ROOT, options.document, options.template, options.typography, options.format, options.venue)
        if options.action == "Lint":
            return lint(ROOT)
        if options.action == "Validate":
            return check_venue(ROOT, options.document, options.template, options.typography, options.venue)
        if options.action == "Package":
            return package(ROOT, options.document, options.template, options.typography, options.venue)
        if options.action == "Test":
            try:
                import pytest
            except ImportError:
                print("pytest is missing; create the project environment with .\\scripts\\setup.ps1", file=sys.stderr)
                return 2
            return int(pytest.main([str(ROOT / "tests"), "-ra"]))
        if options.action == "Watch":
            return watch(ROOT, options.document, options.template or "article", options.typography or "default", options.format, options.venue)
        if options.action == "Clean":
            return clean(ROOT)
        if options.action == "Handoff":
            return generate_handoff(ROOT)
    except (ValueError, OSError, RuntimeError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2
    return 2


def _menu(title: str, choices: list[str], default: str | None = None) -> str:
    if not choices:
        raise ValueError(f"No choices available for {title.lower()}")
    print(title + ":")
    for index, choice in enumerate(choices, 1):
        marker = " (default)" if choice == default else ""
        print(f"  {index}. {choice}{marker}")
    while True:
        answer = input(f"Choose 1-{len(choices)}" + (f" [{choices.index(default) + 1}]" if default in choices else "") + ", or q to cancel: ").strip()
        if answer.lower() in {"q", "quit", "cancel"}:
            raise ValueError("Publishing cancelled")
        if not answer and default in choices:
            return default
        if answer.isdigit() and 1 <= int(answer) <= len(choices):
            return choices[int(answer) - 1]
        print("Invalid selection; enter a listed number or q to cancel.", file=sys.stderr)


if __name__ == "__main__":
    raise SystemExit(main())
