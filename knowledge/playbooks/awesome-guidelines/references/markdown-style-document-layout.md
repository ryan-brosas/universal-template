<!-- capsule-v2 -->
# Document layout — does the page structure scan like Google docguide?

**Source:** Google Markdown style guide §Document layout, §Headings, §Character line limit. **Question:** Will docs render with one title, clear intro, and reviewable 80-column source?

## Structure seam
**Path/Symbol:** `*.md` documentation files.
**Signature:** single H1; 1–3 sentence intro; sections from H2; optional `[TOC]`.
**Data Shape:** ~80-character wrapped prose (exceptions below).

### Decisive pattern
```markdown
# Extending Foo

Foo is the batch processor for nightly exports. This guide covers safe
extension points and testing hooks.

[TOC]

## Prerequisites

You need admin access to the Foo service account.

## See also

* [Foo API reference](/docs/foo/api.md)
```

**Flow:** `#` title ≈ filename → short intro → `[TOC]` before first `##` when host supports → body H2+ → `## See also` for extra links.
**Invariant:** multiple H1 headings or intro after TOC fails review.
**Probe:** markdownlint `single-h1`; manual check title matches path intent.

## Heading seam
```markdown
## Foo summary

Content about Foo.

## Bar summary

Content about Bar.
```

**Flow:** ATX `#` headings only → space after `#` → blank line before/after → unique descriptive heading text (not repeated `### Summary`).
**Invariant:** Setext underlines and `##Heading` without space fail review.
**Probe:** grep `^---$` under headings; heading uniqueness for anchor links.

## Line wrap seam
```markdown
For deployment, run the canary script with the `--dry-run` flag first, then
promote using the standard release checklist documented in
[Release process](/docs/release.md).
```

**Flow:** wrap prose near 80 columns → exceptions: links, tables, headings, fenced code may exceed 80 → no trailing whitespace; prefer paragraph break over `<br>`.
**Invariant:** trailing two-space line breaks fail presubmit; use `\` sparingly for hard breaks.
**Probe:** `markdownlint MD009/MD013` per project config; `git diff --check` clean.

## Verdict
One H1, intro, optional TOC, ATX headings, 80-col prose. Learning note: `markdown-style-learning-note.md`.
