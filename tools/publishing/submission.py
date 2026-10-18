"""Venue inspection and clean IEEE source-bundle creation."""

from __future__ import annotations

import shutil
import subprocess
import sys
import zipfile
import re
from pathlib import Path

from .resolve_document import resolve_document
from .validate import validate


def check_venue(root: Path, document: str, profile: str | None, typography: str | None, venue_name: str | None = None) -> int:
    resolved = resolve_document(root, document, profile, typography, venue_name)
    venue = resolved["venue_config"]
    if not venue:
        raise ValueError("The selected document has no venue configuration")
    if venue.get("illustrative"):
        print("WARNING: venue requirements are illustrative, not official IEEE rules")
    source_errors = validate(root, resolved["manifest"])
    if source_errors:
        print("FAIL source validation:\n" + "\n".join(source_errors), file=sys.stderr)
        return 1
    pdf = root / "build" / document / resolved["profile"] / resolved["typography"] / "pdf" / f"{resolved['output']}.pdf"
    if not pdf.is_file():
        raise ValueError(f"Build the PDF before venue inspection: {pdf.relative_to(root)}")
    if shutil.which("pdfinfo"):
        info = subprocess.run(["pdfinfo", str(pdf)], capture_output=True, text=True, check=False)
        if info.returncode:
            raise ValueError(f"Could not inspect PDF: {info.stderr.strip()}")
        values = dict(line.split(":", 1) for line in info.stdout.splitlines() if ":" in line)
        pages = int(values.get("Pages", "0").strip())
        expected = str(venue.get("paper-size", "letter")).lower()
        page_size = values.get("Page size", "").lower()
        size_matches = {
            "letter": ("612 x 792" in page_size or "612 x 791" in page_size),
            "a4": ("595 x 842" in page_size or "595 x 841" in page_size),
        }.get(expected)
        if size_matches is None:
            print(f"WARNING unsupported page-size inspection value: {expected}")
        elif not size_matches:
            print(f"FAIL page size: expected {expected}, found {page_size}", file=sys.stderr)
            return 1
        print(f"OK page size: {page_size or 'unavailable'}")
        if pages > int(venue.get("page-limit", pages)):
            print(f"FAIL page limit: {pages} exceeds {venue['page-limit']}", file=sys.stderr)
            return 1
        print(f"OK page count: {pages}")
    else:
        print("WARNING pdfinfo unavailable; page size and page count were not checked")
    if shutil.which("pdffonts"):
        fonts = subprocess.run(["pdffonts", str(pdf)], capture_output=True, text=True, check=False)
        if fonts.returncode or any(line.split()[4:5] != ["yes"] for line in fonts.stdout.splitlines()[2:] if line.strip()):
            print("FAIL embedded fonts: one or more PDF fonts are not embedded", file=sys.stderr)
            return 1
        print("OK embedded fonts")
    log = pdf.with_suffix(".log")
    if log.is_file() and ("undefined references" in log.read_text(encoding="utf-8", errors="replace").lower()):
        print("FAIL unresolved references; inspect the LaTeX log", file=sys.stderr)
        return 1
    if venue.get("anonymous"):
        metadata = resolved["manifest"].get("metadata", {})
        if resolved["manifest"].get("authors") or (isinstance(metadata, dict) and metadata.get("authors")):
            print("FAIL author metadata present in anonymous submission", file=sys.stderr)
            return 1
        author_field = values.get("Author", "").strip() if "pdfinfo" in locals() else ""
        if author_field:
            print("FAIL PDF metadata contains an author field", file=sys.stderr)
            return 1
    print("Local checks passed; this is not IEEE certification. Visually review the PDF and use the venue's official checker.")
    return 0


def package(root: Path, document: str, profile: str | None, typography: str | None, venue: str | None = None) -> int:
    resolved = resolve_document(root, document, profile, typography, venue)
    source_errors = validate(root, resolved["manifest"])
    if source_errors:
        raise ValueError("\n".join(source_errors))
    if resolved["profile"] != "ieee-conference":
        raise ValueError("Submission source bundles are currently supported only for ieee-conference")
    build_dir = root / "build" / document / resolved["profile"] / resolved["typography"] / "pdf"
    tex = build_dir / f"{resolved['output']}.tex"
    pdf = build_dir / f"{resolved['output']}.pdf"
    if not tex.is_file() or not pdf.is_file():
        raise ValueError("Build both the standalone LaTeX and PDF before packaging")
    destination = root / "build" / document / resolved["profile"] / resolved["typography"] / "submission"
    destination.mkdir(parents=True, exist_ok=True)
    archive = destination / f"{resolved['output']}-submission.zip"
    manifest = resolved["manifest"]
    class_file = root / "templates/ieee/upstream/IEEEtran.cls"
    files = [tex, pdf, class_file, root / "templates/ieee/upstream/IEEEtran.bst", root / "templates/ieee/conference.tex"]
    files += [root / item for item in manifest["sources"]]
    bibliography = manifest.get("bibliography", [])
    bibliography = [bibliography] if isinstance(bibliography, str) else bibliography
    files += [root / item for item in bibliography]
    files += [root / item for item in manifest.get("assets", [])]
    document_folder = root / manifest["document_folder"]
    for asset_dir in (document_folder / "assets", root / "assets"):
        if asset_dir.is_dir():
            files.extend(path for path in asset_dir.rglob("*") if path.is_file())
    for source in manifest["sources"]:
        source_path = root / source
        text = source_path.read_text(encoding="utf-8")
        for target in re.findall(r"!?\[[^\]]*\]\(([^)]+)\)", text):
            target = target.split()[0].strip("<>")
            if re.match(r"^(?:https?:|data:|#)", target, re.I):
                continue
            candidates = [source_path.parent / target, document_folder / target, root / target]
            asset = next((candidate.resolve() for candidate in candidates if candidate.resolve().is_file()), None)
            if asset is not None:
                files.append(asset)
                if asset.suffix.lower() == ".svg" and asset.with_suffix(".pdf").is_file():
                    files.append(asset.with_suffix(".pdf"))
    files = list(dict.fromkeys(path.resolve() for path in files))
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
        for path in files:
            if not path.is_file():
                raise ValueError(f"Missing submission dependency: {path.relative_to(root)}")
            if path.name.endswith((".log", ".aux", ".fls", ".synctex.gz")):
                continue
            if path == class_file.resolve():
                arcname = Path("IEEEtran.cls")
            else:
                arcname = path.relative_to(build_dir) if path.is_relative_to(build_dir) else path.relative_to(root)
            bundle.write(path, arcname.as_posix())
    print(f"Created {archive.relative_to(root)}")
    return 0
