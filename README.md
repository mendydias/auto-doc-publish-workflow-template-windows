# Windows Academic Markdown Publisher

A PowerShell 7+ interface and Python orchestration layer for ordered academic Markdown documents. This is a Windows-first project; it does not use WSL, containers, Bash, Make, or Unix build utilities.

## Requirements

- Windows 10/11 and PowerShell 7.4 or later.
- Python 3.11+ (3.12 is selected for CI) and project-local dependencies.
- Pandoc 3.1–3.x and a `pandoc-crossref` executable built for the selected Pandoc release.
- For PDF only: LuaLaTeX, latexmk, Perl, kpsewhich, TeX classes/packages, Libertinus Serif, and Libertinus Math.
- The PDF toolchain check compiles a small font probe with LuaLaTeX; `fc-list`/fontconfig are not used.
- Native publishing tool installations are managed by the workstation or runner owner. The project never installs or changes system publishing tools automatically.

Supported and selected toolchain requirements are in `config/toolchain.toml`. A `pandoc-crossref` build-version mismatch is treated as an error. HTML and DOCX do not require the PDF/TeX toolchain; `all` does.

## Project-local Python environment

From any directory, create a project-local `.venv` and install the pinned project dependencies:

```powershell
pwsh -NoProfile -File .\scripts\setup.ps1
```

This script only creates `.venv` and installs the project's pinned Python packages. It does not install PowerShell, TeX, Pandoc, Perl, fonts, or alter execution policy. Troubleshooting execution policy should follow organizational policy; if script execution is blocked, use an approved process-scoped policy or invoke from a permitted PowerShell session rather than changing machine policy.

## Quick start

```powershell
pwsh -NoProfile -File .\publish.ps1 -Action Check
pwsh -NoProfile -File .\publish.ps1
pwsh -NoProfile -File .\publish.ps1 -Action Build -Document example -Profile article -Typography academic -Format pdf
pwsh -NoProfile -File .\publish.ps1 -Action Build -Profile thesis -Format all
pwsh -NoProfile -File .\publish.ps1 -Action Lint
pwsh -NoProfile -File .\publish.ps1 -Action Test
pwsh -NoProfile -File .\publish.ps1 -Action Watch
pwsh -NoProfile -File .\publish.ps1 -Action Clean
```

The public defaults are Build, PDF, document `example`, profile `article`, and typography `default`. Formats are `pdf`, `latex`, `docx`, `html`, `epub`, and `all`. `all` shares one orchestrator and emits each format into its own directory. Only PDF invokes LuaLaTeX. `publish.ps1 -?` shows PowerShell help; Python also provides `python -m tools.publishing --help`.

The project root is resolved from the entry point, not the current directory. Manifest paths are repository-relative. Output paths are `build/<document>/<profile>/<typography>/<format>/`; generated TeX, caches, temporary files, and logs stay under ignored `build/`. Source files are never rewritten.

## Documents and profiles

YAML manifests in `config/documents/` declare an ordered `sources` list, metadata, bibliography, and safe output basename. Ordering is preserved exactly. Profile configuration in `config/profiles/` controls document structure; typography in `config/typography/` controls LaTeX appearance independently. Format settings are isolated in `config/formats/`.

Profiles: `article`, `report`, `thesis`. Typography: `default`, `academic`, `compact`. Add sources/resources with repository-relative paths and commit intentional assets. Keep generated artifacts under `build/`.

The thesis profile uses front matter, Roman numbering before `\mainmatter`, Arabic numbering thereafter, chapter-aware cross-reference numbering from pandoc-crossref, and appendices. The thesis uses the standard Pandoc LaTeX template with narrow header includes rather than a wholesale template replacement. Non-LaTeX renderers do not promise identical pagination or thesis front matter: raw TeX commands and page furniture are LaTeX-specific; HTML/EPUB reflow and DOCX uses Word styles.

## Citations and Zotero

The sample bibliography is `references/references.bib`; the APA 7 CSL is `references/apa.csl`. Its source, author attribution, and CC BY-SA 3.0 licensing are recorded in `references/APA-CSL-PROVENANCE.md` and retained in the style.

For Zotero, use Better BibTeX and stable citation keys. Export a project bibliography to `references/references.bib` (or a dedicated manifest path), configure automatic export to keep it synchronized, review the diff, and commit bibliography updates with the document changes. Keep citekeys stable to avoid broken citations. Cite syntax demonstrates narrative (`@smith2021`), parenthetical, multiple (`[@smith2021; @jones2020]`), and page-specific (`@jones2020, p. 17`) forms. Cross-reference filters run before citeproc; citeproc is enabled once.

## Validation, watch, and cleanup

`Lint` validates YAML manifests, source/resource paths, duplicate BibTeX keys, citation keys, duplicate labels, unresolved cross-references, and Pandoc-parsed Markdown; it then runs pinned Ruff and PyMarkdown with Pandoc-oriented configuration. Negative fixtures and test cases exercise failures. Watch polls source/manifest/resource/template/config inputs, debounces edits, and runs builds synchronously (no overlapping builds); build outputs are not watched. Ctrl+C stops cleanly.

`Clean` removes generated contents only under repository `build/`, retaining `.gitkeep`. It preflights symlinks and Windows junctions and refuses unsafe paths rather than traversing outside the intended directory.

## Tests and GitHub Actions

Run `-Action Test` and `-Action Lint` after setup. Tests inspect DOCX XML, EPUB package contents, and textual exports rather than only checking existence. The workflow uses `windows-2022`, PowerShell, pinned Python and action SHAs. PR jobs target article/thesis PDF and DOCX; main/tag builds include all formats; manual dispatch exposes document/profile/typography/format inputs. Release permissions are scoped to the release job and it depends on successful verification/build jobs.

GitHub-hosted Windows runners are **not assumed** to contain the TeX/Pandoc/crossref/Perl/font toolchain. The workflow explicitly runs dependency checks and records versions, then fails clearly if runner-image prerequisites are missing. Provision these pinned/approved native tools in an organization-managed runner image or approved CI provisioning step; do not interpret a passing YAML/static check as a successful Actions run. Actual Actions success is unverified until the workflow runs.

## Handoff and troubleshooting

Generate a continuation report for a Windows agent:

```powershell
pwsh -NoProfile -File .\scripts\windows-handoff.ps1
```

It writes `build/handoff/windows-handoff.md` and `.json`; it does not run acceptance or install tools. The report includes host/tool discovery, repository state, next steps, and the acceptance checklist.

Common issues:

- **Python missing / Windows Store alias:** install Python independently or create the project `.venv`; disable an unwanted App Execution Alias in Windows Settings if it shadows a real interpreter.
- **pandoc-crossref mismatch:** install a crossref build matching `pandoc --version`; do not silently bypass the filter.
- **LuaLaTeX font unavailable:** install/enable the required Libertinus fonts in the TeX environment and rerun Check; the minimal compilation is authoritative.
- **latexmk fails:** verify Perl is on `PATH`, TeX binaries are on `PATH`, and `latexmk -v` works in the same PowerShell session.
- **DOCX styles differ:** edit the maintained `templates/docx/reference.docx`; Word layout is not expected to match PDF exactly.
- **Execution policy:** do not weaken machine policy automatically; follow local IT guidance and use an approved session-scoped method.

## Limitations and verification status

The renderer formats differ by design: PDF/LaTeX controls pagination and typography; DOCX depends on Word's style/layout engine; HTML/EPUB reflow and have no page furniture. The project is implemented in a Linux development environment, but **Windows acceptance has not been performed**. PowerShell exit behavior, Windows aliases, file locks, junction handling, Windows paths, watch behavior, and native Windows tool versions must be verified with the handoff checklist. Configuration inspection is not evidence of a successful GitHub Actions run.
