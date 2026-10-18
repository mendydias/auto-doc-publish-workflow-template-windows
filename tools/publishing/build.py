"""Shared Pandoc build pipeline."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path
import os

import yaml

from .dependencies import check_dependencies
from .validate import validate
from .resolve_document import resolve_document

FORMATS = ("pdf", "latex", "docx", "html", "epub")


def _command(args: list[str], cwd: Path) -> int:
    try:
        result = subprocess.run(args, cwd=cwd, check=False)
        return result.returncode
    except OSError as error:
        print(f"Cannot start {args[0]}: {error}", file=sys.stderr)
        return 127


def build(root: Path, document: str, profile: str | None, typography: str | None, format_name: str, venue: str | None = None) -> int:
    try:
        import yaml
    except ImportError as error:
        raise RuntimeError("PyYAML is missing; create the project environment with .\\scripts\\setup.ps1") from error
    resolved = resolve_document(root, document, profile, typography, venue)
    manifest = resolved["manifest"]
    profile = resolved["profile"]
    typography = resolved["typography"]
    defaults_path = root / "config/defaults/common.yaml"
    if not defaults_path.is_file():
        defaults_path = root / "config/pandoc.yaml"
    shared_defaults = yaml.safe_load(defaults_path.read_text(encoding="utf-8")) or {}
    profile_config = resolved["profile_config"]
    typography_config = resolved["typography_config"]
    validation_errors = validate(root, manifest)
    if validation_errors:
        raise ValueError("\n".join(validation_errors))
    supported_formats = profile_config.get("formats", list(FORMATS))
    if format_name != "all" and format_name not in supported_formats:
        raise ValueError(f"Format '{format_name}' is not supported by profile '{profile}'")
    if profile == "ieee-conference":
        return _build_ieee(root, resolved, format_name, shared_defaults)
    formats = tuple(supported_formats) if format_name == "all" else (format_name,)
    if check_dependencies(root, format_name):
        return 1
    sources = [root / item for item in manifest["sources"]]
    bibliography = manifest.get("bibliography", [])
    bibliography = [bibliography] if isinstance(bibliography, str) else bibliography
    base_output = root / "build" / document / profile / typography
    for output_format in formats:
        output_dir = base_output / output_format
        output_dir.mkdir(parents=True, exist_ok=True)
        config_record = {
            "document": document, "template": profile, "typography": typography,
            "venue": resolved["venue"], "format": output_format,
            "basename": resolved["output"], "supported_formats": list(supported_formats),
            "metadata": manifest.get("metadata", {}),
        }
        (output_dir / "resolved-config.yaml").write_text(yaml.safe_dump(config_record, sort_keys=False), encoding="utf-8")
        basename = resolved["output"]
        extension = "tex" if output_format == "latex" else output_format
        output = output_dir / f"{basename}.{extension}"
        args = [shutil.which("pandoc") or "pandoc", *map(str, sources)]
        for key, value in shared_defaults.items():
            option = key.replace("_", "-")
            if isinstance(value, bool):
                if value:
                    args.append(f"--{option}")
            else:
                args += [f"--{option}", str(value)]
        resource_paths = [root.resolve(), (root / manifest["resource_base"]).resolve(), *(source.resolve().parent for source in sources)]
        args += ["--to", "latex" if output_format in ("latex", "pdf") else output_format, "--output", str(output), "--resource-path", os.pathsep.join(dict.fromkeys(map(str, resource_paths)))]
        format_defaults = yaml.safe_load((root / "config/formats" / f"{output_format}.yaml").read_text(encoding="utf-8")) or {}
        latex_settings = {**profile_config, **typography_config} if output_format in ("pdf", "latex") else {}
        for key, value in {**format_defaults, **latex_settings}.items():
            if key in ("from", "to", "standalone", "filters", "pdf-engine", "css", "reference-doc", "epub-chapter-level", "embed-resources", "include-before-body", "include-in-header"):
                continue
            option = key.replace("_", "-")
            if key == "numbersections":
                if value:
                    args.append("--number-sections")
            elif key == "documentclass":
                args += ["--metadata", f"documentclass={value}"]
            elif isinstance(value, bool):
                if value:
                    args.append(f"--{option}")
            elif isinstance(value, list):
                for item in value:
                    args += ["--variable", f"{key}={item}"]
            else:
                args += ["--variable", f"{key}={value}"]
        if profile == "thesis":
            args += ["--metadata", "chapters=true", "--top-level-division=chapter"]
            if output_format in ("pdf", "latex"):
                args += ["--include-in-header", str(root / "templates/latex/thesis-header.tex")]
        if output_format == "docx":
            reference_doc = format_defaults.get("reference-doc", "templates/docx/reference.docx")
            args += ["--reference-doc", str(root / reference_doc)]
        if output_format in ("html", "epub"):
            for css_path in format_defaults.get("css", []):
                args += ["--css", str(root / css_path)]
            if format_defaults.get("embed-resources"):
                args.append("--embed-resources")
        if output_format == "epub" and format_defaults.get("epub-chapter-level"):
            args += ["--epub-chapter-level", str(format_defaults["epub-chapter-level"])]
        if output_format == "pdf":
            args += ["--pdf-engine", "lualatex"]
        if output_format in ("pdf", "latex"):
            args += ["--lua-filter", str(root / "templates/latex/svg-to-pdf.lua"), "--include-in-header", str(root / "templates/latex/typography.tex")]
            document_folder = Path(manifest["document_folder"])
            if (root / document_folder / "assets").is_dir():
                asset_header = output_dir / "document-assets.tex"
                asset_header.write_text(f"\\graphicspath{{{{{document_folder.as_posix()}/}}}}\n", encoding="utf-8")
                args += ["--include-in-header", str(asset_header)]
        metadata = dict(manifest.get("metadata", {}))
        for key in ("title", "author", "authors", "date", "abstract", "keywords"):
            if manifest.get(key) is not None:
                metadata[key] = manifest[key]
        metadata_file = output_dir / "pandoc-metadata.yaml"
        metadata_file.write_text(yaml.safe_dump(metadata, allow_unicode=True, sort_keys=False), encoding="utf-8")
        args += ["--metadata-file", str(metadata_file)]
        if bibliography:
            for bibliography_path in bibliography:
                args += ["--bibliography", str(root / bibliography_path)]
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
            code = _command([shutil.which("latexmk") or "latexmk", "-lualatex", "-interaction=nonstopmode", "-halt-on-error", "-file-line-error", f"-outdir={output_dir}", str(tex)], root)
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


def _build_ieee(root: Path, resolved: dict, format_name: str, shared_defaults: dict) -> int:
    """Build the class-controlled IEEE profile with the profile's safe tool choices."""
    if format_name not in ("pdf", "latex"):
        raise ValueError("IEEE conference profile supports only latex and pdf")
    manifest = resolved["manifest"]
    profile = resolved["profile_config"]
    document = resolved["document"]
    typography = resolved["typography"]
    engine = profile.get("latex-engine", "pdflatex")
    required = ["pandoc", engine]
    if format_name == "pdf":
        required.extend(["latexmk", "bibtex"] if profile.get("bibliography", {}).get("processor") == "bibtex" else ["latexmk"])
    missing = [name for name in required if not shutil.which(name)]
    if missing:
        raise RuntimeError("Missing required tools for this build: " + ", ".join(missing))
    output_dir = root / "build" / document / resolved["profile"] / typography / format_name
    output_dir.mkdir(parents=True, exist_ok=True)
    output = output_dir / f"{resolved['output']}.{'tex' if format_name == 'latex' else 'pdf'}"
    tex_output = output if format_name == "latex" else output_dir / f"{resolved['output']}.tex"
    config_record = {key: value for key, value in resolved.items() if key != "manifest"}
    config_record["manifest"] = manifest
    (output_dir / "resolved-config.yaml").write_text(yaml.safe_dump(config_record, sort_keys=False), encoding="utf-8")
    args = [shutil.which("pandoc") or "pandoc", *[str(root / source) for source in manifest["sources"]]]
    for key, value in shared_defaults.items():
        if key in {"from", "standalone"}:
            args += [f"--{key}", str(value)] if key == "from" else ["--standalone"]
    sources = [root / source for source in manifest["sources"]]
    resource_paths = [root.resolve(), (root / manifest["resource_base"]).resolve(), *(source.resolve().parent for source in sources)]
    args += ["--to", "latex", "--template", str(root / profile["template"]), "--output", str(tex_output), "--resource-path", os.pathsep.join(dict.fromkeys(map(str, resource_paths)))]
    metadata = dict(manifest.get("metadata", {}))
    for key in ("title", "author", "authors", "date", "abstract", "keywords"):
        if manifest.get(key) is not None:
            metadata[key] = manifest[key]
    metadata_file = output_dir / "pandoc-metadata.yaml"
    metadata_file.write_text(yaml.safe_dump(metadata, allow_unicode=True, sort_keys=False), encoding="utf-8")
    args += ["--metadata-file", str(metadata_file)]
    args += ["--variable", f"documentclass={profile.get('documentclass', 'IEEEtran')}"]
    args += ["--variable", "float-placement=b"]
    document_folder = Path(manifest["document_folder"])
    args += ["--variable", f"document-assets={document_folder.as_posix()}/"]
    for option in profile.get("classoption", []):
        args += ["--variable", f"classoption={option}"]
    bibliography_style = profile.get("bibliography", {}).get("style")
    if bibliography_style:
        args += ["--variable", f"bibliography-style={Path(bibliography_style).with_suffix('').as_posix()}"]
    if profile.get("number-sections"):
        args.append("--number-sections")
    if profile.get("top-level-division"):
        args += ["--top-level-division", profile["top-level-division"]]
    bibliography = manifest.get("bibliography", [])
    if isinstance(bibliography, str):
        bibliography = [bibliography]
    processor = profile.get("bibliography", {}).get("processor", "citeproc")
    for source in bibliography:
        args += ["--bibliography", str(root / source)]
    bibliography_paths = [Path(source).with_suffix("").as_posix() for source in bibliography]
    if bibliography_paths:
        args += ["--variable", f"bibliography={','.join(bibliography_paths)}"]
    if processor == "bibtex":
        args.append("--natbib")
    elif bibliography:
        args.append("--citeproc")
    result = _command(args, root)
    if result or format_name == "latex":
        return result
    command = [shutil.which("latexmk") or "latexmk", "-pdf", f"-pdflatex={engine} %O %S", "-interaction=nonstopmode", "-halt-on-error", "-file-line-error", f"-outdir={output_dir}", str(output_dir / f"{resolved['output']}.tex")]
    result = _command(command, root)
    log_path = output_dir / f"{resolved['output']}.log"
    if not result and log_path.is_file():
        import re

        log_text = log_path.read_text(encoding="utf-8", errors="replace")
        unresolved = re.findall(r"(?:Citation|Reference) `[^']+' .*?undefined", log_text)
        if unresolved:
            print("Unresolved LaTeX references:\n" + "\n".join(sorted(set(unresolved))), file=sys.stderr)
            return 1
    if not result:
        print(f"Built {output.relative_to(root)}")
    return result
