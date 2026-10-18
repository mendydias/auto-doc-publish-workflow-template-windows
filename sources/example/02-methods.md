# Methods {#sec:methods}

This second source demonstrates ordered composition and cross-file references. The result is summarized in @tbl:summary.

| Format | Purpose |
|:--|:--|
| PDF | Print-ready document |
| DOCX | Editable review copy |
| HTML | Accessible web publication |
| EPUB | Reflowable reading |

: Supported publication formats {#tbl:summary}

```python
def ordered_sources(manifest):
    return list(manifest["sources"])
```
{#lst:manifest caption="Manifest ordering"}
