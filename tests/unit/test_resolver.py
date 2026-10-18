from pathlib import Path
import shutil

import pytest

from tools.publishing.resolve_document import resolve_document
from tools.publishing.build import build


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
    assert second["manifest"]["bibliography"] == ["sources/ieee-example/references.bib"]
    assert second["profile"] == "ieee-conference"
    assert second["typography"] == "ieee"


def test_unified_document_builds_without_legacy_manifest_and_owns_defaults(tmp_path: Path, monkeypatch) -> None:
    shutil.copytree(ROOT / "config", tmp_path / "config")
    folder = tmp_path / "sources/new-paper"
    (folder / "sections").mkdir(parents=True)
    (folder / "sections/01-start.md").write_text("A cited work [@new-key].", encoding="utf-8")
    (folder / "refs-one.bib").write_text("@book{new-key, title={New}, year={2026}}", encoding="utf-8")
    (folder / "refs-two.bib").write_text("@book{second-key, title={Second}, year={2026}}", encoding="utf-8")
    (folder / "assets").mkdir()
    (folder / "assets/figure.svg").write_text("<svg/>", encoding="utf-8")
    (folder / "document.yaml").write_text(
        "title: Updated Title\nauthors:\n  - name: Author\ntemplate: article\n"
        "typography: academic\nvenue: example-conference\nbasename: custom-name\n"
        "bibliography: [refs-one.bib, refs-two.bib]\nassets: [assets/figure.svg]\n",
        encoding="utf-8",
    )
    resolved = resolve_document(tmp_path, "new-paper")
    assert resolved["manifest"]["title"] == "Updated Title"
    assert resolved["manifest"]["output"] == "custom-name"
    assert resolved["profile"] == "article"
    assert resolved["typography"] == "academic"
    assert resolved["venue"] == "example-conference"
    assert resolved["manifest"]["bibliography"] == [
        "sources/new-paper/refs-one.bib", "sources/new-paper/refs-two.bib"
    ]
    assert resolved["manifest"]["assets"] == ["sources/new-paper/assets/figure.svg"]

    commands: list[list[str]] = []
    monkeypatch.setattr("tools.publishing.build.validate", lambda *_: [])
    monkeypatch.setattr("tools.publishing.build.check_dependencies", lambda *_: 0)
    monkeypatch.setattr("tools.publishing.build._command", lambda args, _cwd: commands.append(args) or 0)
    assert build(tmp_path, "new-paper", None, None, "latex") == 0
    pandoc_args = commands[0]
    assert pandoc_args.count("--bibliography") == 2
    metadata_file = Path(pandoc_args[pandoc_args.index("--metadata-file") + 1])
    assert "Updated Title" in metadata_file.read_text(encoding="utf-8")
    assert "custom-name.tex" in pandoc_args[pandoc_args.index("--output") + 1]
