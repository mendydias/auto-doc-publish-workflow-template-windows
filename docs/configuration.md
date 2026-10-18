# Configuration reference

## Author documents

New documents live in `sources/<document-id>/`. The directory name supplies
the ID and default basename. `document.yaml` contains metadata and optional
`template`, `typography`, `venue`, `sections`, `bibliography`, and `assets`
values. Numbered Markdown under `sections/` is ordered numerically; an
explicit ordered `sections` list overrides discovery. Resource paths are
relative to the document folder and must not escape it. See
[the authoring contract](authoring-contract.md) for the shared schema and
template-specific metadata requirements.

All publishing commands require `sources/<id>/document.yaml`. There is no
legacy manifest fallback. Sections, bibliographies, and assets belong in the
document folder; resource paths are relative to it. Shared profiles, venues,
typography, formats, and renderer templates remain maintainer-owned under
`config/` and `templates/`.

## Shared publishing configuration

| Location | Owns |
|---|---|
| `config/profiles/<id>.yaml` | Document class/options, structure, numbering, LaTeX engine, bibliography processor/style, typography defaults/allowlist, supported formats, restrictions |
| `config/venues/<id>.yaml` | Illustrative flag, page size/count, anonymity, named submission checks |
| `config/typography/<id>.yaml` | Typography preset; class-controlled mode delegates layout to the class |
| `config/formats/<format>.yaml` | Renderer options isolated by output format |
| `config/defaults/common.yaml` | Shared Pandoc reader and standalone settings |
| `templates/` | Maintained renderer templates and their assets |
| `build/` | Generated output, logs, caches, setup diagnostics, and resolved settings |

Document IDs, template IDs, typography IDs, and venue IDs use letters, digits, hyphens,
and underscores. The renderer validates repository boundaries and safe output
basenames. Supported LaTeX engines are `pdflatex`, `lualatex`, and `xelatex`;
bibliography processors are `citeproc`, `bibtex`, and `biber`. Configuration
never supplies executable command strings.

## Options and precedence

The shared CLI/environment option names are `PUBLISH_DOCUMENT`,
`PUBLISH_TEMPLATE`, `PUBLISH_FORMAT`, `PUBLISH_ACTION`,
`PUBLISH_NON_INTERACTIVE`, `PUBLISH_TYPOGRAPHY`, and `PUBLISH_VENUE`.
Precedence is explicit CLI options, environment, document defaults, then
application defaults. `--profile` is a compatibility alias for `--template`;
conflicting values are rejected. The PowerShell wrapper forwards only options
explicitly supplied on its command line.

The build writes effective settings to
`build/<document>/<template>/<typography>/<format>/resolved-config.yaml`.
Generated files and caches should not be committed. Cleanup is constrained to
the repository's `build/` directory and refuses unsafe paths.
