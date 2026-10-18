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

## Unified publishing acceptance status

The authoring contract and sample `sources/<id>/document.yaml` files are
consumed by all publishing actions. Unit and integration tests cover discovery,
numeric section ordering, Unicode filenames, duplicate section numbers,
traversal, symlink escapes, CLI option precedence, and incremental IEEE
bibliography edits on Linux. Unified source folders are the only supported
authoring input. The Windows bootstrap has only been edited and statically
inspected here:
WinGet package installation, agreements, TeX/font provisioning, setup
repeatability, and actual Windows PowerShell behavior remain unverified. Do not
treat this record as completion of Windows acceptance.
