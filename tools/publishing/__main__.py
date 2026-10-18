"""CLI entry point; all paths are rooted at the repository, never the caller's cwd."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .build import build
from .clean import clean
from .dependencies import check_dependencies
from .validate import lint
from .watch import watch
from .handoff import generate as generate_handoff
from .submission import check_venue, package
from .options import resolve_options

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


if __name__ == "__main__":
    raise SystemExit(main())
