# IEEE conference example

This repository includes a complete illustrative IEEE conference manuscript.
It demonstrates the workflow and IEEEtran class, but is **not an IEEE-approved
template**, and its example venue limits are not official requirements.

## Authoring layout

The only author-facing copy is `sources/ieee-example/`: metadata is in
`document.yaml`, ordered sections are under `sections/`, the bibliography is
beside the document metadata, and document assets are under `assets/`. New IEEE
documents should copy this folder and update its structured `authors`,
`abstract`, `keywords`, template, venue, and bibliography values.

## Build and inspect

Use the repository virtual environment after installing project dependencies
and the approved Pandoc/TeX tools:

```powershell
pwsh -NoProfile -File .\publish.ps1 -Action Build -Document ieee-example -Format latex
pwsh -NoProfile -File .\publish.ps1 -Action Build -Document ieee-example -Format pdf
pwsh -NoProfile -File .\publish.ps1 -Action Validate -Document ieee-example
pwsh -NoProfile -File .\publish.ps1 -Action Package -Document ieee-example
```

Equivalent Python CLI calls use `python -m tools.publishing` with the same
`--action`, `--document`, and `--format` options. Output is isolated under
`build/ieee-example/ieee-conference/ieee/`; the PDF folder contains the
standalone `.tex`, resolved configuration, PDF, and transient TeX build files.
The submission ZIP is under the `submission/` directory and deliberately
omits logs, caches, and SyncTeX residue.

`Validate` checks configured page size/page count when `pdfinfo` is available,
embedded fonts when `pdffonts` is available, and unresolved references. These
are local diagnostics, not venue certification. Review the complete PDF
visually and use the conference's official submission checker.

## Shared renderer configuration

- `config/profiles/ieee-conference.yaml` selects IEEEtran, the custom template,
  pdfLaTeX, BibTeX/IEEEtran.bst, supported formats, and typography restrictions.
- `config/typography/ieee.yaml` delegates typography to the IEEEtran class.
- `config/venues/example-conference.yaml` shows where venue limits/checks live;
  all values are explicitly illustrative.
- `config/defaults/common.yaml` contains only shared Pandoc input/standalone
  behavior. It must not grow venue-specific layout options.

CLI `--template` (`--profile` alias) and `--typography` selections override
manifest/profile defaults only when the profile allows the requested preset.
All paths are repository-relative and validated against traversal.

## Citations, equations, figures, and tables

For IEEE BibTeX, use stable citekeys (Better BibTeX for Zotero is suitable),
keep the exported `.bib` file in version control, and cite with Markdown
`[@key]` syntax. The IEEE profile uses Pandoc's `--natbib` adapter and BibTeX;
citeproc is not enabled for this build. `latexmk` runs BibTeX using the pinned
`IEEEtran.bst` from `templates/ieee/upstream/`. The example includes a numbered
equation, a two-column-compatible LaTeX table, a figure, and section/cross-file
references. Raw LaTeX is intentionally used where the IEEE two-column layout
requires explicit control.

## Assets and limitations

`templates/ieee/UPSTREAM.md` records archive checksums, known provenance, and
retained upstream notices. The `.zip` archives are preserved; runtime extracts
include the class and default (unsorted) IEEEtran BibTeX style. This profile
currently supports LaTeX and PDF only. Journal-specific layouts, other export
formats, official IEEE validation, and Windows/Podman/Docker acceptance remain
unverified or future work.
