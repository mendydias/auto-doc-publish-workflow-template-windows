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
    assert pdf.is_file()

    assert package(ROOT, "ieee-example", None, None) == 0
    archive = output / "submission/ieee-example-submission.zip"
    with zipfile.ZipFile(archive) as bundle:
        names = set(bundle.namelist())
    assert "IEEEtran.cls" in names
    assert "src/ieee-example/references.bib" in names
    assert "assets/workflow.pdf" in names
    assert not any(name.endswith((".log", ".aux", ".fls", ".synctex.gz")) for name in names)
