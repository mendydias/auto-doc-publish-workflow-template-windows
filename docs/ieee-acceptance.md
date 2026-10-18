# IEEE publishing acceptance record

Verified in the Linux development environment on 2026-10-18:

- Native `latex` and `pdf` publication with Pandoc, pdfLaTeX, latexmk, and
  BibTeX using the local IEEEtran class and `IEEEtran.bst`.
- One-page PDF output inspected as an image and by extracted text; citations,
  equations, cross-references, captions, and embedded fonts resolved.
- Illustrative venue checks reported US Letter, page count, and embedded fonts.
- Submission ZIP rebuilt independently from an extracted temporary directory.
- Python tests: 42 passed, one Windows-only test skipped. Ruff and Markdown
  lint passed.

The generated PDF, intermediate LaTeX/log files, resolved build configuration,
and submission ZIP are in ignored `build/`; generated publications are not
source-controlled. The archives remain unchanged. This workflow does not
provide IEEE certification. Venue values are illustrative; authors must
manually review the PDF and run the official checker for their actual venue.

Not verified: Windows acceptance, Podman, Docker, official IEEE submission
validation, anonymous-submission review, or cross-platform TeX toolchain
equivalence. The independent bundle rebuild used the available local Linux
TeX installation.

## Unified workflow acceptance status

The updated authoring contract and sample `sources/<id>/document.yaml` files
are present, and unit tests cover discovery, numeric section ordering, Unicode
filenames, duplicate section numbers, traversal, symlink escapes, and CLI
option precedence. The new-layout loader is not yet consumed by the main
renderers; legacy manifests remain required for real builds. The Windows
bootstrap and workflow have only been edited and statically inspected here:
WinGet package installation, agreements, TeX/font provisioning, setup
repeatability, actual Windows PowerShell behavior, and GitHub Actions execution
remain unverified. Do not treat this record as completion of Windows acceptance.
