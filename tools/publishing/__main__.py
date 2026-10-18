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

ROOT = Path(__file__).resolve().parents[2]


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description="Build and validate academic Markdown publications.")
    result.add_argument("--action", choices=["Check", "Build", "Lint", "Validate", "Package", "Test", "Watch", "Clean", "Handoff"], default="Build")
    result.add_argument("--document", default="example")
    result.add_argument("--profile", default=None, help="Publication profile (defaults to the document manifest)")
    result.add_argument("--typography", default=None, help="Typography preset (defaults to the selected profile)")
    result.add_argument("--venue", default=None, help="Venue rules (defaults to the document manifest)")
    result.add_argument("--format", dest="format", choices=["pdf", "latex", "docx", "html", "epub", "all"], default="pdf")
    return result


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.action == "Check":
            return check_dependencies(ROOT, args.format)
        if args.action == "Build":
            return build(ROOT, args.document, args.profile, args.typography, args.format, args.venue)
        if args.action == "Lint":
            return lint(ROOT)
        if args.action == "Validate":
            return check_venue(ROOT, args.document, args.profile, args.typography, args.venue)
        if args.action == "Package":
            return package(ROOT, args.document, args.profile, args.typography, args.venue)
        if args.action == "Test":
            try:
                import pytest
            except ImportError:
                print("pytest is missing; create the project environment with .\\scripts\\setup.ps1", file=sys.stderr)
                return 2
            return int(pytest.main([str(ROOT / "tests"), "-ra"]))
        if args.action == "Watch":
            return watch(ROOT, args.document, args.profile or "article", args.typography or "default", args.format)
        if args.action == "Clean":
            return clean(ROOT)
        if args.action == "Handoff":
            return generate_handoff(ROOT)
    except (ValueError, OSError, RuntimeError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
