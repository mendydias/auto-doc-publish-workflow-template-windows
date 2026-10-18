"""CLI entry point; all paths are rooted at the repository, never the caller's cwd."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .build import build
from .clean import clean
from .dependencies import check_dependencies
from .validate import lint, validate
from .watch import watch

ROOT = Path(__file__).resolve().parents[2]


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description="Build and validate academic Markdown publications.")
    result.add_argument("--action", choices=["Check", "Build", "Lint", "Test", "Watch", "Clean"], default="Build")
    result.add_argument("--document", default="example")
    result.add_argument("--profile", choices=["article", "report", "thesis"], default="article")
    result.add_argument("--typography", choices=["default", "academic", "compact"], default="default")
    result.add_argument("--format", dest="format", choices=["pdf", "latex", "docx", "html", "epub", "all"], default="pdf")
    return result


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.action == "Check":
            return check_dependencies(ROOT, args.format)
        if args.action == "Build":
            return build(ROOT, args.document, args.profile, args.typography, args.format)
        if args.action == "Lint":
            return lint(ROOT)
        if args.action == "Test":
            import pytest
            return int(pytest.main([str(ROOT / "tests"), "-ra"]))
        if args.action == "Watch":
            return watch(ROOT, args.document, args.profile, args.typography, args.format)
        if args.action == "Clean":
            return clean(ROOT)
    except (ValueError, OSError, RuntimeError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
