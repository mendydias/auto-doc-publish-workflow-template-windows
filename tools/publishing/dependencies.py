"""Operation-scoped native tool discovery and compatibility checks."""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
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
    if any(item in formats for item in ("pdf", "latex")):
        required.extend(["pandoc-crossref", *PDF_TOOLS])
    failed = False
    for name in dict.fromkeys(required):
        code, text = _run(name, ["--version"] if name not in ("kpsewhich",) else ["--version"])
        first_line = text.splitlines()[0] if text else "no version output"
        print(f"{'OK' if code == 0 else 'MISSING'} {name}: {first_line}")
        failed |= code != 0
    if sys.version_info < (3, 11):
        print("MISSING Python: requires 3.11 or later")
        failed = True
    if "pdf" in formats:
        for package in ("article.cls", "fontspec.sty", "unicode-math.sty", "xurl.sty"):
            code, text = _run("kpsewhich", [package])
            if code or not text.strip():
                print(f"MISSING TeX package/class: {package}")
                failed = True
            else:
                print(f"OK TeX resource: {package}")
    return 1 if failed else 0
