from pathlib import Path
import shutil

import pytest

from tools.publishing.resolve_document import resolve_document


ROOT = Path(__file__).resolve().parents[2]


def test_manifest_selects_ieee_profile_and_typography() -> None:
    config = resolve_document(ROOT, "ieee-example")
    assert (config["profile"], config["typography"], config["venue"]) == (
        "ieee-conference", "ieee", "example-conference"
    )


def test_profile_restrictions_cannot_be_overridden() -> None:
    with pytest.raises(ValueError, match="not allowed by profile"):
        resolve_document(ROOT, "ieee-example", typography="compact")


def test_cli_profile_selection_overrides_manifest_default() -> None:
    config = resolve_document(ROOT, "example", profile="report")
    assert config["profile"] == "report"


def test_new_numbered_sections_override_legacy_source_list(tmp_path: Path) -> None:
    for directory in ("config", "sources/ieee-example", "src/ieee-example", "templates"):
        shutil.copytree(ROOT / directory, tmp_path / directory)

    first = resolve_document(tmp_path, "ieee-example")
    assert [Path(source).name for source in first["manifest"]["sources"]] == [
        "01-introduction.md", "02-related-work.md", "03-methods.md",
        "04-results.md", "05-conclusion.md",
    ]

    section = tmp_path / "sources/ieee-example/sections/06-sample.md"
    section.write_text("# Sample\n", encoding="utf-8")
    second = resolve_document(tmp_path, "ieee-example")
    assert Path(second["manifest"]["sources"][-1]).name == "06-sample.md"
