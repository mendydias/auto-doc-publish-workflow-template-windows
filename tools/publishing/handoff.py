"""Generate a portable status/acceptance handoff for a Windows continuation agent."""

from __future__ import annotations

import json
import platform
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


ACCEPTANCE = [
    "pwsh -NoProfile -File .\\publish.ps1 -Action Check",
    "pwsh -NoProfile -File .\\publish.ps1 -Action Build",
    "pwsh -NoProfile -File .\\publish.ps1 -Action Build -Document example -Profile article -Typography academic -Format pdf",
    "pwsh -NoProfile -File .\\publish.ps1 -Action Build -Profile thesis -Format all",
    "pwsh -NoProfile -File .\\publish.ps1 -Action Lint",
    "pwsh -NoProfile -File .\\publish.ps1 -Action Test",
    "pwsh -NoProfile -File .\\publish.ps1 -Action Watch (edit a source, observe one debounced rebuild, then Ctrl+C)",
    "pwsh -NoProfile -File .\\publish.ps1 -Action Clean",
    "Invoke from a different working directory and from a checkout path containing spaces and non-ASCII characters",
    "Verify all profiles (article/report/thesis), all formats, and typography presets (default/academic/compact)",
    "Inspect PDF text, generated TeX, DOCX XML, HTML, EPUB package; check citations, references, numbering, Unicode, appendices",
    "Assert non-PDF builds do not start LuaLaTeX; check source hashes unchanged and cleanup cannot escape build/",
]


def _command_version(name: str, args: list[str]) -> dict[str, object]:
    executable = shutil.which(name)
    if not executable:
        return {"available": False, "path": None, "version": None}
    try:
        result = subprocess.run([executable, *args], capture_output=True, text=True, timeout=15, check=False)
        text = (result.stdout + result.stderr).strip()
        return {"available": result.returncode == 0, "path": executable, "version": text.splitlines()[0] if text else "", "exit_code": result.returncode}
    except (OSError, subprocess.TimeoutExpired) as error:
        return {"available": False, "path": executable, "error": str(error)}


def generate(root: Path) -> int:
    build = root / "build"
    report_dir = build / "handoff"
    report_dir.mkdir(parents=True, exist_ok=True)
    git = subprocess.run(["git", "-C", str(root), "status", "--short", "--branch"], capture_output=True, text=True, check=False)
    commit = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"], capture_output=True, text=True, check=False)
    tools = {name: _command_version(name, args) for name, args in {
        "pwsh": ["-NoProfile", "-Command", "$PSVersionTable.PSVersion.ToString()"],
        "python": ["--version"], "pandoc": ["--version"], "pandoc-crossref": ["--version"],
        "lualatex": ["--version"], "latexmk": ["-v"], "kpsewhich": ["--version"], "perl": ["--version"],
    }.items()}
    checks = [
        {"name": name, "status": "PASS" if info.get("available") else "FAIL", "detail": info.get("version", info.get("error", "not found"))}
        for name, info in tools.items()
    ]
    checks.extend([
        {"name": "Windows-native acceptance", "status": "UNVERIFIED", "detail": "Requires Windows 10/11 and PowerShell 7+; report generation does not execute acceptance."},
        {"name": "GitHub Actions execution", "status": "UNVERIFIED", "detail": "Workflow configuration is not evidence of a successful run."},
    ])
    payload = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "repository": str(root), "commit": commit.stdout.strip() or None,
        "git_status": git.stdout.strip(), "host": platform.platform(),
        "python": sys.version, "tools": tools, "checks": checks,
        "implemented": ["PowerShell/Python CLI", "ordered YAML manifests", "article/report/thesis profiles", "PDF/LaTeX/DOCX/HTML/EPUB pipeline", "AST-driven citation/reference/resource validation", "typography presets", "watch and cleanup", "semantic export tests", "Windows Actions workflow"],
        "verification_boundary": "This report does not perform Windows acceptance. Linux checks and mocks do not establish Windows support.",
        "acceptance_commands": ACCEPTANCE,
    }
    json_path = report_dir / "windows-handoff.json"
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = ["# Windows continuation and acceptance handoff", "", f"Generated (UTC): {payload['generated_utc']}", f"Repository: `{root}`", f"Commit: `{payload['commit']}`", f"Host: `{payload['host']}`", "", "## Working tree", "", "```text", payload["git_status"], "```", "", "## Tool discovery", "", "| Tool | Available | Version |", "|---|---:|---|"]
    for name, details in tools.items():
        version = str(details.get("version", details.get("error", "not found"))).replace("|", "\\|")
        lines.append(f"| `{name}` | {details.get('available', False)} | {version} |")
    lines += ["", "## Checks", "", "| Check | Status | Detail |", "|---|---|---|"]
    for check in checks:
        detail = str(check["detail"]).replace("|", "\\|")
        lines.append(f"| {check['name']} | **{check['status']}** | {detail} |")
    lines += ["", "## Continue safely", "", "1. Review the current commit and working tree before editing; preserve uncommitted work.", "2. Read `README.md`, `config/toolchain.toml`, and the repository's Windows verification notes.", "3. On Windows 10/11 with PowerShell 7+, install only project-local Python dependencies using `pwsh -NoProfile -File .\\scripts\\setup.ps1` (publishing tools are managed separately by the workstation/runner owner).", "4. Run the acceptance commands below and record exact outcomes. Do not claim acceptance based on Linux or mocked runs.", "5. Fix failures in focused increments and commit each completed plan step; keep generated artifacts under ignored `build/`.", "", "## Required Windows acceptance", ""]
    lines.extend(f"- [ ] `{command}`" for command in ACCEPTANCE)
    lines += ["", "## Known verification boundary", "", str(payload["verification_boundary"]), "The workflow file can be inspected statically here, but no GitHub Actions run or Windows acceptance is claimed.", ""]
    md_path = report_dir / "windows-handoff.md"
    md_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {md_path.relative_to(root)}")
    print(f"Wrote {json_path.relative_to(root)}")
    return 0
