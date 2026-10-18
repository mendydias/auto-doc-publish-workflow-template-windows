# Academic Markdown Publisher

Prepare a Windows workstation once, then edit documents under `sources/` and
publish them with the guided command:

```powershell
.\setup.ps1
.\publish.ps1
```

The setup uses WinGet and may request agreement acceptance. Review the
packages and their agreements before running it. To run unattended, use
`-NonInteractive -AcceptAgreements`. It does not change execution policy or
silently elevate. Setup logs are written to `build/setup/`.

## Author documents

Each publication lives in its own folder. Copy a folder to start another
document, then update its metadata and content:

```text
sources/
  my-paper/
    document.yaml
    sections/
      01-introduction.md
      02-methods.md
    references.bib
    assets/
      figure.svg
```

The folder name is the document ID and default output basename. `document.yaml`
contains the title, structured authors, and optional template, typography,
venue, abstract, keywords, and bibliography settings. Numbered Markdown files
directly under `sections/` are ordered numerically. An explicit ordered
`sections` list can be used when needed. Bibliographies and assets belong in
the document folder; their paths are relative to that folder.

Example metadata:

```yaml
title: A Reproducible Study
authors:
  - name: Morgan Researcher
    affiliation: Example University
    email: morgan@example.edu
date: "2026"
template: article
bibliography: references.bib
```

Use standard Pandoc Markdown, citations backed by the document's BibTeX file,
and image paths relative to the document folder. See
[the complete authoring contract](docs/authoring-contract.md),
[IEEE walkthrough](docs/ieee-authoring.md), and the shipped documents in
`sources/` for examples. IEEE documents additionally require an abstract,
keywords, and author affiliations.

## Publishing

With multiple documents, `publish.ps1` displays a numbered document menu and a
template menu. A single document is selected automatically. The default format
is PDF; template restrictions and defaults are applied during validation.
Artifacts and diagnostics are kept under `build/<document>/`. Generated files
are not source files and can be recreated at any time.

For automation, provide choices through environment variables; scripts do
not prompt in CI or when stdin is redirected:

```powershell
$env:PUBLISH_DOCUMENT = 'ieee-example'
$env:PUBLISH_TEMPLATE = 'ieee-conference'
$env:PUBLISH_FORMAT = 'pdf'
$env:PUBLISH_NON_INTERACTIVE = '1'
.\publish.ps1
```

Supported variables are `PUBLISH_DOCUMENT`, `PUBLISH_TEMPLATE`,
`PUBLISH_FORMAT`, `PUBLISH_ACTION`, `PUBLISH_NON_INTERACTIVE`,
`PUBLISH_TYPOGRAPHY`, and `PUBLISH_VENUE`. Explicit CLI options override
environment values. `--profile` / `-Profile` remains a compatibility alias
for the template option.

## Advanced use and configuration

Shared configuration belongs in `config/`, maintained templates in
`templates/`, and generated output in `build/`. Template-specific metadata and
format support are documented in [configuration reference](docs/configuration.md).
The Python entrypoint also supports validation, linting, watch, packaging, and
cleanup actions; see `python -m tools.publishing --help`.

The repository still carries compatibility support for legacy manifests in
`config/documents/`. New authoring should use the folder layout above. The
normalized loader and renderer migration is not yet complete, so existing
publishing commands continue to resolve legacy manifests until that integration
is finished.

## Verification and limitations

Run `python -m pytest` for the test suite. The current Linux development run
passed 54 tests with one Windows-only test skipped. Static workflow edits are
not evidence of a
successful GitHub Actions run. Windows setup, WinGet package availability,
MiKTeX package/font provisioning, PDF smoke tests, and end-to-end publishing
must still be verified on a real Windows machine. In particular, the bootstrap
currently provisions the primary tools and Python environment but does not yet
automate every TeX package, font, or pinned `pandoc-crossref` check described
in the toolchain plan.
