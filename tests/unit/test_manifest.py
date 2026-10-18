from pathlib import Path

import pytest

from tools.publishing.validate import validate


@pytest.mark.parametrize("name,expected", [("traversal.yaml", "escapes repository"), ("missing-resource.yaml", "Missing resource")])
def test_negative_manifests_are_rejected(name: str, expected: str) -> None:
    root = Path(__file__).resolve().parents[2]
    errors = validate(root, root / "tests/fixtures/negative" / name)
    assert any(expected in error for error in errors)


def test_duplicate_bibliography_keys_are_rejected() -> None:
    root = Path(__file__).resolve().parents[2]
    errors = validate(root, root / "tests/fixtures/negative/duplicate-bibliography.yaml")
    assert any("Duplicate bibliography key: same" in error for error in errors)


def test_example_manifest_validates_citations_and_references() -> None:
    root = Path(__file__).resolve().parents[2]
    assert validate(root, root / "config/documents/example.yaml") == []


def test_duplicate_labels_missing_citation_and_unresolved_reference_fail() -> None:
    root = Path(__file__).resolve().parents[2]
    errors = validate(root, root / "tests/fixtures/negative/invalid-references.yaml")
    assert any("Duplicate label: repeated" in error for error in errors)
    assert any("Missing citation key: not-in-bibliography" in error for error in errors)
    assert any("Unresolved cross-reference: fig:not-present" in error for error in errors)
