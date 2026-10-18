"""Artifact-semantic smoke checks for tools available on the host."""

import shutil
import subprocess
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize("format_name,extension", [("html", ".html"), ("docx", ".docx"), ("epub", ".epub"), ("latex", ".tex")])
def test_pandoc_exports_have_semantic_content(tmp_path: Path, format_name: str, extension: str) -> None:
    pandoc = shutil.which("pandoc")
    if not pandoc:
        pytest.skip("Pandoc is unavailable")
    output = tmp_path / ("sample" + extension)
    args = [pandoc, str(ROOT / "sources/example/01-introduction.md"), str(ROOT / "sources/example/02-methods.md"), "--standalone", "--resource-path", str(ROOT), "--output", str(output)]
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
