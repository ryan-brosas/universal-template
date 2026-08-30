---
name: markdown-writing-practices
description: "Use when authoring or reviewing Markdown docs — single H1 layout, 80-column wrap, ATX headings, fenced code with language, descriptive links, reference links, and tables only when scannable 2D data."
disable-model-invocation: true
---

# Markdown Writing Practices

Application skill for Markdown style learning (`awesome-guidelines` deep ingest). For HTML/CSS page templates, load `frontend-markup-practices`. For platform wiki syntax (Confluence), use stack conventions.

## Core Principle

Documentation Markdown is **maintainable plain text** — one H1, wrapped prose, fenced code, descriptive links, minimal HTML.

## When to Use / NOT

- README, skills, ADRs, handbook pages, repo docs under `docs/` or `references/`.
- Reviewing doc PRs for structure and link hygiene.

**NOT when:**

- Generated API docs from source comments — validate generator templates.
- Rich wiki with non-Markdown macros only — use platform foundation.

## Workflow

1. **Layout** — H1, intro, TOC, headings, 80-col wrap (`markdown-style-document-layout.md`).
2. **Lists & code** — lazy numbering, fences, languages (`markdown-style-lists-code.md`).
3. **Links & media** — paths, reference links, alt text (`markdown-style-links-media.md`).
4. **Tables** — 2D data only; Markdown not HTML (`markdown-style-tables-portability.md`).
5. **Verify** — markdownlint/remark + `git diff --check` on changed `.md` files.

## Red Flags

- Multiple H1 or Setext headings
- `[here](url)` / bare URL link text
- `../../` relative link chains
- Indented code blocks without language
- Trailing whitespace for line breaks
- HTML layout where Markdown suffices
- Tables that should be lists
- Images without alt text

## Verification

- markdownlint (or project remark config) on changed files
- `git diff --check` clean
- Render preview spot-check for TOC, fences, tables
- Capsule checklist on doc review

## Skill Result Contract

```xml
<skill_result>
  <skill>markdown-writing-practices</skill>
  <status>success|partial|blocked|failure</status>
  <artifacts>md diff, markdownlint output</artifacts>
  <evidence>learning note + capsule probes cited</evidence>
  <risks>fragile links, missing alt, HTML drift, or none</risks>
</skill_result>
```

## References

- `awesome-guidelines/references/markdown-style-learning-note.md`
- `awesome-guidelines/references/markdown-style-document-layout.md`
- `awesome-guidelines/references/markdown-style-lists-code.md`
- `awesome-guidelines/references/markdown-style-links-media.md`
- `awesome-guidelines/references/markdown-style-tables-portability.md`
