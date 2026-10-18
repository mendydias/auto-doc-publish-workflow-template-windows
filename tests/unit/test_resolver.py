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
    for directory in ("config", "sources/ieee-example", "templates"):
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
    shutil.copytree(ROOT / "templates", tmp_path / "templates")
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
    monkeypatch.setattr("tools.publishing.build._command", lambda args, _cwd, **kwargs: commands.append(args) or 0)
    assert build(tmp_path, "new-paper", None, None, "latex") == 0
    pandoc_args = commands[0]
    assert pandoc_args.count("--bibliography") == 2
    metadata_file = Path(pandoc_args[pandoc_args.index("--metadata-file") + 1])
    assert "Updated Title" in metadata_file.read_text(encoding="utf-8")
    assert "custom-name.tex" in pandoc_args[pandoc_args.index("--output") + 1]


def test_configured_template_and_header_are_passed_to_pandoc(tmp_path: Path, monkeypatch) -> None:
    shutil.copytree(ROOT / "config", tmp_path / "config")
    shutil.copytree(ROOT / "templates", tmp_path / "templates")
    shutil.copytree(ROOT / "sources/example", tmp_path / "sources/example")
    profile = tmp_path / "config/profiles/article.yaml"
    profile.write_text(
        profile.read_text(encoding="utf-8")
        + "template: templates/latex/custom.tex\n"
        + "include-in-header: [templates/latex/custom-header.tex]\n",
        encoding="utf-8",
    )
    (tmp_path / "templates/latex/custom.tex").write_text("CUSTOM TEMPLATE", encoding="utf-8")
    header = tmp_path / "templates/latex/custom-header.tex"
    header.write_text(r"\setlength{\headheight}{9pt}", encoding="utf-8")
    monkeypatch.setattr("tools.publishing.build.validate", lambda *_: [])
    monkeypatch.setattr("tools.publishing.build.check_dependencies", lambda *_: 0)
    commands: list[list[str]] = []
    monkeypatch.setattr("tools.publishing.build._command", lambda args, *_args, **_kwargs: commands.append(args) or 0)

    assert build(tmp_path, "example", "article", "default", "latex") == 0
    args = commands[0]
    assert args[args.index("--template") + 1] == str(tmp_path / "templates/latex/custom.tex")
    assert str(header) in args


def test_missing_profile_include_is_rejected(tmp_path: Path) -> None:
    shutil.copytree(ROOT / "config", tmp_path / "config")
    shutil.copytree(ROOT / "templates", tmp_path / "templates")
    shutil.copytree(ROOT / "sources/thesis", tmp_path / "sources/thesis")
    profile = tmp_path / "config/profiles/thesis.yaml"
    profile.write_text(profile.read_text(encoding="utf-8") + "include-before-body: [templates/latex/missing.tex]\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Missing or unsafe profile include-before-body resource"):
        resolve_document(tmp_path, "thesis")
