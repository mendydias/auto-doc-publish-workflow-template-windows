"""Artifact-semantic smoke checks for tools available on the host."""

import shutil
import subprocess
import zipfile
import os
import shutil as file_shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize("profile", ["article", "report", "thesis"])
@pytest.mark.parametrize("format_name", ["pdf", "latex", "docx", "html", "epub"])
def test_manifest_build_matrix_has_semantic_artifacts(profile: str, format_name: str) -> None:
    from tools.publishing.build import build

    if not shutil.which("pandoc"):
        pytest.skip("Pandoc is unavailable")
    source_paths = [ROOT / "sources/example/sections/01-introduction.md", ROOT / "sources/example/sections/02-methods.md"]
    before = [path.read_bytes() for path in source_paths]
    assert build(ROOT, "example", profile, "academic", format_name) == 0
    output_dir = ROOT / "build/example" / profile / "academic" / format_name
    suffix = "tex" if format_name == "latex" else format_name
    artifact = output_dir / f"example.{suffix}"
    assert artifact.is_file()
    if format_name == "pdf":
        from pypdf import PdfReader
        text = "\n".join(page.extract_text() or "" for page in PdfReader(artifact).pages)
        assert "Introduction" in text and "Methods" in text
        assert "Jones" in text and "Smith" in text
        assert "A schematic workflow" in text
        assert "naïve" in text
    elif format_name == "latex":
        text = artifact.read_text(encoding="utf-8")
        assert "\\documentclass" in text and "\\begin{document}" in text
        assert "\\label{fig:workflow}" in text and "\\label{tbl:summary}" in text
        assert text.index("Introduction}") < text.index("Methods}")
    elif format_name == "docx":
        with zipfile.ZipFile(artifact) as package:
            xml = package.read("word/document.xml").decode("utf-8")
        assert "Introduction" in xml and "Methods" in xml and "Smith" in xml
    elif format_name == "epub":
        with zipfile.ZipFile(artifact) as package:
            assert package.read("mimetype").startswith(b"application/epub+zip")
            text = b" ".join(package.read(name) for name in package.namelist() if name.endswith((".xhtml", ".html")))
        assert b"Introduction" in text and b"ref-smith2021" in text
    else:
        text = artifact.read_text(encoding="utf-8")
        assert "Introduction" in text and "Smith" in text and "ref-smith2021" in text
    assert [path.read_bytes() for path in source_paths] == before


def test_non_pdf_build_does_not_invoke_latex(monkeypatch) -> None:
    from tools.publishing import build as build_module

    monkeypatch.setattr(build_module, "check_dependencies", lambda *_: 0)
    monkeypatch.setattr(build_module, "validate", lambda *_: [])
    invocations = []
    monkeypatch.setattr(build_module, "_command", lambda args, cwd, **kwargs: (invocations.append(args) or 0))
    assert build_module.build(ROOT, "example", "article", "default", "html") == 0
    assert all("latexmk" not in " ".join(args).lower() and "lualatex" not in " ".join(args).lower() for args in invocations)


def test_repeated_build_is_successful_and_semantically_stable() -> None:
    from tools.publishing.build import build

    assert build(ROOT, "example", "article", "default", "html") == 0
    artifact = ROOT / "build/example/article/default/html/example.html"
    first = artifact.read_text(encoding="utf-8")
    assert build(ROOT, "example", "article", "default", "html") == 0
    second = artifact.read_text(encoding="utf-8")
    assert "ref-smith2021" in first and "ref-smith2021" in second
    assert "fig:workflow" in first and "fig:workflow" in second


def test_thesis_template_edit_is_used_by_next_build(tmp_path: Path) -> None:
    from tools.publishing.build import build

    if not shutil.which("pandoc"):
        pytest.skip("Pandoc is unavailable")
    for directory in ("config", "templates", "sources/thesis", "references"):
        shutil.copytree(ROOT / directory, tmp_path / directory)
    header = tmp_path / "templates/latex/thesis-header.tex"
    output_dir = tmp_path / "build/thesis/thesis/academic/pdf"
    tex = output_dir / "thesis.tex"
    pdf = output_dir / "thesis.pdf"

    assert build(tmp_path, "thesis", None, None, "pdf") == 0
    assert pdf.is_file()
    assert r"\setlength{\headheight}{14pt}" in tex.read_text(encoding="utf-8")
    header.write_text(header.read_text(encoding="utf-8").replace("14pt", "9pt"), encoding="utf-8")
    assert build(tmp_path, "thesis", None, None, "pdf") == 0
    assert pdf.is_file()
    rendered = tex.read_text(encoding="utf-8")
    assert r"\setlength{\headheight}{9pt}" in rendered
    assert r"\pagestyle{fancy}" in rendered
    assert r"\pagestyle{plain}" not in rendered

    header.write_text(r"\undefinedthesiscommand", encoding="utf-8")
    assert build(tmp_path, "thesis", None, None, "pdf") != 0


def test_unicode_checkout_and_invocation_from_another_directory(tmp_path: Path) -> None:
    if not shutil.which("pandoc") or not shutil.which("pandoc-crossref"):
        pytest.skip("Pandoc toolchain is unavailable")
    checkout = tmp_path / "Checkout with spaces – 東京"
    ignore = file_shutil.ignore_patterns(".git", ".venv", "build", "__pycache__", ".pytest_cache")
    file_shutil.copytree(ROOT, checkout, ignore=ignore)
    caller = tmp_path / "unrelated working directory"
    caller.mkdir()
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(checkout)
    result = subprocess.run([sys.executable, "-m", "tools.publishing", "--action", "Build", "--document", "example", "--profile", "article", "--typography", "default", "--format", "html"], cwd=caller, env=environment, capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stdout + result.stderr
    assert (checkout / "build/example/article/default/html/example.html").is_file()


def test_power_shell_propagates_python_failure_on_windows() -> None:
    if os.name != "nt":
        pytest.skip("Windows PowerShell exit propagation requires Windows")
    pwsh = shutil.which("pwsh")
    if not pwsh:
        pytest.skip("PowerShell 7 is unavailable")
    result = subprocess.run([pwsh, "-NoProfile", "-File", str(ROOT / "publish.ps1"), "-Action", "Build", "-Document", "does-not-exist"], cwd=ROOT.parent, check=False)
    assert result.returncode == 2


@pytest.mark.parametrize("format_name,extension", [("html", ".html"), ("docx", ".docx"), ("epub", ".epub"), ("latex", ".tex")])
def test_pandoc_exports_have_semantic_content(tmp_path: Path, format_name: str, extension: str) -> None:
    pandoc = shutil.which("pandoc")
    if not pandoc:
        pytest.skip("Pandoc is unavailable")
    output = tmp_path / ("sample" + extension)
    args = [pandoc, str(ROOT / "sources/example/sections/01-introduction.md"), str(ROOT / "sources/example/sections/02-methods.md"), "--standalone", "--resource-path", str(ROOT / "sources/example"), "--output", str(output)]
    if format_name == "latex":
        args += ["--to", "latex"]
    else:
        args += ["--to", format_name]
    result = subprocess.run(args, cwd=ROOT, capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr
    if extension == ".docx":
        with zipfile.ZipFile(output) as package:
            xml = package.read("word/document.xml").decode("utf-8")
        assert "Introduction" in xml and "Methods" in xml
    elif extension == ".epub":
        with zipfile.ZipFile(output) as package:
            names = package.namelist()
            assert "mimetype" in names
            contents = b" ".join(package.read(name) for name in names if name.endswith((".xhtml", ".html")))
        assert b"Introduction" in contents and b"Methods" in contents
    else:
        text = output.read_text(encoding="utf-8")
        assert "Introduction" in text and "Methods" in text
