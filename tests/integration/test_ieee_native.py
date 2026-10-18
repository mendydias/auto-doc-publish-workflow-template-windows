from __future__ import annotations

import shutil
import zipfile
from pathlib import Path

import pytest

from tools.publishing.build import build
from tools.publishing.submission import package

ROOT = Path(__file__).resolve().parents[2]
TOOLS = ("pandoc", "pdflatex", "latexmk", "bibtex")


@pytest.mark.skipif(any(not shutil.which(tool) for tool in TOOLS), reason="IEEE native toolchain unavailable")
def test_ieee_latex_pdf_and_submission_bundle() -> None:
    assert build(ROOT, "ieee-example", None, None, "latex") == 0
    assert build(ROOT, "ieee-example", None, None, "pdf") == 0
    output = ROOT / "build/ieee-example/ieee-conference/ieee"
    latex = output / "latex/ieee-example.tex"
    pdf = output / "pdf/ieee-example.pdf"
    tex = latex.read_text(encoding="utf-8")
    assert r"\documentclass[conference]{IEEEtran}" in tex
    assert "geometry" not in tex and "fontspec" not in tex and "unicode-math" not in tex
    assert r"\bibliographystyle{templates/ieee/upstream/IEEEtran}" in tex
    assert r"\bibliography{sources/ieee-example/references}" in tex
    assert pdf.is_file()
    fls = (output / "pdf/ieee-example.fls").read_text(encoding="utf-8")
    assert str(ROOT / "templates/ieee/upstream/IEEEtran.cls") in fls

    assert package(ROOT, "ieee-example", None, None) == 0
    archive = output / "submission/ieee-example-submission.zip"
    with zipfile.ZipFile(archive) as bundle:
        names = set(bundle.namelist())
    assert "IEEEtran.cls" in names
    assert "sources/ieee-example/references.bib" in names
    assert "sources/ieee-example/assets/workflow.pdf" in names
    assert not any(name.endswith((".log", ".aux", ".fls", ".synctex.gz")) for name in names)


@pytest.mark.skipif(any(not shutil.which(tool) for tool in TOOLS), reason="IEEE native toolchain unavailable")
def test_ieee_bibliography_only_edit_refreshes_pdf_incrementally(tmp_path: Path) -> None:
    import subprocess

    for directory in ("config", "templates", "sources/ieee-example"):
        shutil.copytree(ROOT / directory, tmp_path / directory)
    bib = tmp_path / "sources/ieee-example/references.bib"
    assert build(tmp_path, "ieee-example", None, None, "pdf") == 0
    bbl = tmp_path / "build/ieee-example/ieee-conference/ieee/pdf/ieee-example.bbl"
    before = bbl.read_text(encoding="utf-8")
    marker = "https://incremental-url.example.test/updated"
    bib.write_text(
        bib.read_text(encoding="utf-8").replace(
            "year = {1994}", f"year = {{1994}},\n  url = {{{marker}}}"
        ),
        encoding="utf-8",
    )
    assert marker not in before
    assert build(tmp_path, "ieee-example", None, None, "pdf") == 0
    updated = bbl.read_text(encoding="utf-8")
    assert marker in updated
    pdf = tmp_path / "build/ieee-example/ieee-conference/ieee/pdf/ieee-example.pdf"
    if shutil.which("pdftotext"):
        text = subprocess.run(["pdftotext", str(pdf), "-"], capture_output=True, text=True, check=True).stdout
        assert marker in "".join(text.split())
