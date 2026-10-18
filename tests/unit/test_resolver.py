from pathlib import Path

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
