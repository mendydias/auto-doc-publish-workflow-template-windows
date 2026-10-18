from pathlib import Path

import pytest

from tools.publishing.documents import discover_documents, load_document


def test_discovery_includes_new_and_legacy_documents(tmp_path: Path) -> None:
    (tmp_path / "sources/new").mkdir(parents=True)
    (tmp_path / "sources/new/document.yaml").write_text("title: New\n", encoding="utf-8")
    (tmp_path / "config/documents").mkdir(parents=True)
    (tmp_path / "config/documents/old.yaml").write_text("sources: []\n", encoding="utf-8")
    assert discover_documents(tmp_path) == ["new", "old"]


def test_new_document_orders_numbered_sections_and_resolves_resources(tmp_path: Path) -> None:
    folder = tmp_path / "sources/paper"
    (folder / "sections").mkdir(parents=True)
    (folder / "sections/10-end.md").write_text("end", encoding="utf-8")
    (folder / "sections/02-start.md").write_text("start", encoding="utf-8")
    (folder / "refs.bib").write_text("", encoding="utf-8")
    (folder / "document.yaml").write_text(
        "title: Paper\nauthors:\n  - name: A. Author\nbibliography: refs.bib\n", encoding="utf-8"
    )
    result = load_document(tmp_path, "paper")
    assert [path.name for path in result["sections"]] == ["02-start.md", "10-end.md"]
    assert result["bibliography"] == [(folder / "refs.bib").resolve()]
    assert result["basename"] == "paper"


@pytest.mark.parametrize("path", ["../outside.md", "/absolute.md"])
def test_document_rejects_unsafe_explicit_section_paths(tmp_path: Path, path: str) -> None:
    folder = tmp_path / "sources/paper"
    folder.mkdir(parents=True)
    (folder / "document.yaml").write_text(
        f"title: Paper\nauthors:\n  - name: A. Author\nsections: [{path!r}]\n", encoding="utf-8"
    )
    with pytest.raises(ValueError, match="relative path|escapes document"):
        load_document(tmp_path, "paper")


def test_document_rejects_duplicate_section_numbers(tmp_path: Path) -> None:
    folder = tmp_path / "sources/paper"
    (folder / "sections").mkdir(parents=True)
    for name in ("01-first.md", "01-second.md"):
        (folder / "sections" / name).write_text(name, encoding="utf-8")
    (folder / "document.yaml").write_text("title: Paper\nauthors:\n  - name: A\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Duplicate section"):
        load_document(tmp_path, "paper")


def test_document_supports_unicode_and_spaces_in_folder_and_file_names(tmp_path: Path) -> None:
    folder = tmp_path / "sources" / "paper"
    (folder / "sections").mkdir(parents=True)
    (folder / "sections/01-café introduction.md").write_text("Unicode — café", encoding="utf-8")
    (folder / "document.yaml").write_text("title: Café\nauthors:\n  - name: Zoë\n", encoding="utf-8")
    document = load_document(tmp_path, "paper")
    assert document["sections"][0].name == "01-café introduction.md"


def test_document_rejects_symlink_escape(tmp_path: Path) -> None:
    folder = tmp_path / "sources/paper"
    (folder / "sections").mkdir(parents=True)
    outside = tmp_path / "outside.md"
    outside.write_text("outside", encoding="utf-8")
    try:
        (folder / "sections/01-outside.md").symlink_to(outside)
    except OSError as error:
        pytest.skip(f"symlink creation unavailable: {error}")
    (folder / "document.yaml").write_text("title: Paper\nauthors:\n  - name: A\n", encoding="utf-8")
    with pytest.raises(ValueError, match="escapes document"):
        load_document(tmp_path, "paper")
