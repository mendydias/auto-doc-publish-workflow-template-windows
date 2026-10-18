# Unified authoring and publishing contract

This project uses one author-facing layout for articles, reports, theses, and
IEEE papers. A complete document is a portable folder under `sources/`:

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

## Document identity and metadata

The folder name is the document ID and, unless explicitly overridden, the
output basename. IDs are stable, safe path components (letters and digits,
with internal hyphens or underscores). `document.yaml` is the single source
of publication metadata and may also select default template, typography, or
venue settings. Metadata is a YAML mapping; templates may require additional
fields and must report those requirements explicitly.

Authors use one structured representation across all templates:

```yaml
authors:
  - name: Morgan Researcher
    affiliation: Example University
    email: morgan@example.edu
```

Template-specific information (for example IEEE abstract and keywords, or
thesis front matter) remains metadata in `document.yaml`; it does not require
a separate source layout. A document may give an explicit ordered section
list when the default ordering is insufficient. Otherwise, Markdown files
directly inside `sections/` are discovered and ordered by their leading
integer, then by filename. Duplicate numbers are errors. Nested Markdown is
not implicitly included.

## Resource paths and section content

Bibliography files, figures, and other author resources live inside the
document folder. Resource paths in metadata are relative to that folder, not
the repository or process working directory. Absolute paths, parent traversal,
and symlinks resolving outside the document folder are rejected. Bibliography
may be a single path or an ordered list of paths. Markdown image references
follow the same document-relative rule. Raw LaTeX resource use is explicitly
template/format-specific and must not silently rely on repository-root files.

Section Markdown is regular Pandoc Markdown. Numbered filenames communicate
order, not heading text. Files are concatenated in resolved order. Citations
use the configured bibliography processor, with citation keys defined by the
document's bibliography. Assets are committed alongside the document when
they are required to reproduce its output.

## Publishing configuration and outputs

Author content and metadata belong in `sources/`; shared publishing
configuration belongs in `config/`; render templates and maintained template
assets belong in `templates/`; generated files, intermediates, diagnostics,
and caches belong in `build/`. Publishing must not rewrite author sources.

The selected template owns its supported formats, defaults, and restrictions.
`all` means every format supported by that selected template. Article, report,
and thesis templates may share the standard renderer while applying different
structure and metadata rules. IEEE is a dedicated template and supports PDF
and LaTeX only; unsupported formats fail validation before external tools are
invoked. Venue rules are optional document defaults or explicit overrides and
do not change the underlying authoring layout.

The command-line interface and GitHub Actions use the same publishing
configuration. CLI values override environment values, which override
document defaults, which override application defaults. Interactive
selection is only a local convenience; unattended execution must have
unambiguous document and template selections and must never prompt.

## Template-specific metadata

The unified layout does not imply identical metadata requirements. Standard
academic templates require a non-empty title and structured authors. Thesis
metadata may include dedication, acknowledgements, and front-matter fields.
IEEE additionally requires a non-empty abstract, keywords, and author
affiliations. These requirements are validated by the selected template and
documented in that template's authoring guide. Missing required metadata is an
actionable validation error, not a reason to fall back to another template.

This contract is the target authoring interface. Legacy manifests may be
accepted temporarily during migration, but new documents should use this
layout exclusively.
