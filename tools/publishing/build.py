"""Shared Pandoc build pipeline."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

from .dependencies import check_dependencies
from .validate import validate

FORMATS = ("pdf", "latex", "docx", "html", "epub")


def _command(args: list[str], cwd: Path) -> int:
    try:
        result = subprocess.run(args, cwd=cwd, check=False)
        return result.returncode
    except OSError as error:
        print(f"Cannot start {args[0]}: {error}", file=sys.stderr)
        return 127


def build(root: Path, document: str, profile: str, typography: str, format_name: str) -> int:
    try:
        import yaml
    except ImportError as error:
        raise RuntimeError("PyYAML is missing; create the project environment with .\\scripts\\setup.ps1") from error
    manifest_path = root / "config/documents" / f"{document}.yaml"
    if not manifest_path.is_file():
        raise ValueError(f"Document manifest not found: {manifest_path.relative_to(root)}")
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    profile_config = yaml.safe_load((root / "config/profiles" / f"{profile}.yaml").read_text(encoding="utf-8"))
    typography_config = yaml.safe_load((root / "config/typography" / f"{typography}.yaml").read_text(encoding="utf-8"))
    validate(root, manifest_path)
    formats = FORMATS if format_name == "all" else (format_name,)
    if check_dependencies(root, format_name):
        return 1
    sources = [root / item for item in manifest["sources"]]
    bibliography = manifest.get("bibliography")
    base_output = root / "build" / document / profile / typography
    for output_format in formats:
        output_dir = base_output / output_format
        output_dir.mkdir(parents=True, exist_ok=True)
        basename = manifest["output"]
        extension = "tex" if output_format == "latex" else output_format
        output = output_dir / f"{basename}.{extension}"
        args = [shutil.which("pandoc") or "pandoc", *map(str, sources), "--standalone", "--from", "markdown+tex_math_dollars+raw_tex+fenced_divs+bracketed_spans", "--to", "latex" if output_format in ("latex", "pdf") else output_format, "--output", str(output), "--resource-path", str(root)]
        format_defaults = yaml.safe_load((root / "config/formats" / f"{output_format}.yaml").read_text(encoding="utf-8")) or {}
        latex_settings = {**profile_config, **typography_config} if output_format in ("pdf", "latex") else {}
        for key, value in {**format_defaults, **latex_settings}.items():
            if key in ("from", "to", "standalone", "filters", "pdf-engine", "css", "reference-doc", "epub-chapter-level", "embed-resources", "include-before-body", "include-in-header"):
                continue
            if isinstance(value, bool):
                if value:
                    args.append(f"--{key}")
            elif isinstance(value, list):
                for item in value:
                    args += [f"--{key}", str(item)]
            else:
                args += [f"--{key}", str(value)]
        if profile == "thesis" and output_format in ("pdf", "latex"):
            args += ["--include-in-header", str(root / "templates/latex/thesis-header.tex")]
        if output_format == "docx":
            args += ["--reference-doc", str(root / "templates/docx/reference.docx")]
        if output_format in ("html", "epub"):
            args += ["--css", str(root / "templates/html/academic.css")]
        if output_format == "pdf":
            args += ["--pdf-engine", "lualatex"]
        for key in ("title", "author", "date"):
            if manifest.get(key) is not None:
                args += ["--metadata", f"{key}={manifest[key]}"]
        for key, value in manifest.get("metadata", {}).items():
            args += ["--metadata", f"{key}={value}"]
        if bibliography:
            args += ["--bibliography", str(root / bibliography)]
            csl = root / "references/apa.csl"
            if csl.is_file():
                args += ["--csl", str(csl)]
        crossref = shutil.which("pandoc-crossref")
        if crossref and output_format in ("pdf", "latex", "docx", "html", "epub"):
            args += ["--filter", crossref]
        if bibliography:
            args.append("--citeproc")
        if output_format == "pdf":
            # Preserve standalone TeX, then compile it with latexmk in an isolated output directory.
            tex = output_dir / f"{basename}.tex"
            args[args.index(str(output))] = str(tex)
            code = _command(args, root)
            if code:
                return code
            code = _command([shutil.which("latexmk") or "latexmk", "-lualatex", "-interaction=nonstopmode", "-halt-on-error", "-file-line-error", "-outdir=.", tex.name], output_dir)
            if code:
                return code
            built = output_dir / f"{basename}.pdf"
            if built != output and built.exists():
                built.replace(output)
        else:
            code = _command(args, root)
            if code:
                return code
        print(f"Built {output.relative_to(root)}")
    return 0
