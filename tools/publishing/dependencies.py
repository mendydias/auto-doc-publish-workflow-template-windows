"""Operation-scoped native tool discovery and compatibility checks."""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

PDF_TOOLS = ("lualatex", "latexmk", "kpsewhich")


def _run(name: str, args: list[str]) -> tuple[int, str]:
    path = shutil.which(name)
    if not path:
        return 127, f"{name}: not found on PATH"
    try:
        result = subprocess.run([path, *args], capture_output=True, text=True, timeout=20, check=False)
        return result.returncode, (result.stdout + result.stderr).strip()
    except (OSError, subprocess.TimeoutExpired) as error:
        return 1, f"{name}: {error}"


def check_dependencies(root: Path, format_name: str) -> int:
    formats = ["pdf", "latex", "docx", "html", "epub"] if format_name == "all" else [format_name]
    required = ["pandoc"]
    if any(item in formats for item in ("pdf", "latex", "docx", "html", "epub")):
        required.append("pandoc-crossref")
    if "pdf" in formats:
        required.extend([*PDF_TOOLS, "perl"])
    failed = False
    versions: dict[str, str] = {}
    for name in dict.fromkeys(required):
        code, text = _run(name, ["--version"] if name not in ("kpsewhich",) else ["--version"])
        first_line = text.splitlines()[0] if text else "no version output"
        versions[name] = first_line
        print(f"{'OK' if code == 0 else 'MISSING'} {name}: {first_line}")
        failed |= code != 0
    if "pandoc" in versions and "pandoc-crossref" in versions:
        pandoc_version = re.search(r"pandoc\s+(\d+)\.(\d+)", versions["pandoc"], re.I)
        crossref_version = re.search(r"built with Pandoc v?(\d+)\.(\d+)", versions["pandoc-crossref"], re.I)
        if pandoc_version and crossref_version and pandoc_version.group(1, 2) != crossref_version.group(1, 2):
            print(f"INCOMPATIBLE pandoc-crossref built for {crossref_version.group(1)}.{crossref_version.group(2)} but Pandoc is {pandoc_version.group(1)}.{pandoc_version.group(2)}")
            failed = True
    if sys.version_info < (3, 11):
        print("MISSING Python: requires 3.11 or later")
        failed = True
    if "pdf" in formats:
        for package in ("article.cls", "report.cls", "fontspec.sty", "unicode-math.sty", "xurl.sty"):
            code, text = _run("kpsewhich", [package])
            if code or not text.strip():
                print(f"MISSING TeX package/class: {package}")
                failed = True
            else:
                print(f"OK TeX resource: {package}")
        # Verify real font resolution by compiling, not by consulting fontconfig or fc-list.
        tex_root = root / "build" / "cache" / "font-probe"
        tex_root.mkdir(parents=True, exist_ok=True)
        source = tex_root / "font-probe.tex"
        source.write_text(r"\documentclass{article}" "\n" r"\usepackage{fontspec}" "\n" r"\usepackage{unicode-math}" "\n" r"\setmainfont{Libertinus Serif}" "\n" r"\setmathfont{Libertinus Math}" "\n" r"\begin{document}Unicode — naïve café; $\\alpha+1$.\end{document}" "\n", encoding="utf-8")
        code, text = _run("lualatex", ["-interaction=nonstopmode", "-halt-on-error", "-output-directory", str(tex_root), str(source)])
        if code:
            print("FONT PROBE FAILED: Libertinus Serif / Libertinus Math did not resolve in LuaLaTeX")
            print("\n".join(text.splitlines()[-12:]))
            failed = True
        else:
            print("OK fonts: Libertinus Serif and Libertinus Math resolved in LuaLaTeX")
    return 1 if failed else 0
