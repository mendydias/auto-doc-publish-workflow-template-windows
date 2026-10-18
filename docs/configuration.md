# Publication configuration contract

All manifest and profile resource paths are relative to the repository root.
Document IDs, profile IDs, typography IDs, and venue IDs use letters, digits,
hyphens, and underscores; path traversal is rejected. CLI choices take
precedence over the document manifest, which takes precedence over project
fallbacks. A profile's allowed typography/formats are mandatory restrictions,
not defaults that a CLI option can bypass.

| Configuration | Owned fields |
|---|---|
| `config/documents/<id>.yaml` | `id`, `basename` (legacy `output`), `profile`, `venue`, metadata path or inline mapping, ordered bibliography paths, ordered Markdown `sources` |
| `config/profiles/<id>.yaml` | document class/options, structure, top-level division, numbering, template, LaTeX engine, bibliography processor/style, typography default/allowlist, supported formats, restrictions |
| `config/venues/<id>.yaml` | illustrative flag, page size/count, anonymity, and named submission checks |
| `config/typography/<id>.yaml` | typography preset; `mode: class-controlled` delegates all visual rules to the class |
| `config/defaults/common.yaml` | shared Pandoc input reader and standalone behavior only |

Source/bibliography/metadata/resource paths must resolve inside the repository.
The output basename is a single safe identifier. Supported LaTeX engines are
`pdflatex`, `lualatex`, and `xelatex`; bibliography processors are `citeproc`,
`bibtex`, and `biber`. These values select built-in adapters—configuration
never supplies executable command strings. Container execution choices
(`native`, `podman`, `docker`) are separate from the profile's LaTeX engine;
the current IEEE implementation uses the existing native Windows-first
launcher, with container alternatives not yet integrated/verified.

`build/<document>/<profile>/<typography>/<format>/resolved-config.yaml`
records the effective settings for a build. Generated output/logs/caches remain
under ignored `build/` and should not be committed.
