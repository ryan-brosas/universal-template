---
title: markdown-writing-practices
summary: Use when authoring or reviewing Markdown docs, single H1 layout, 80-column wrap, ATX headings, fenced code with language, descriptive links, reference links, and tables only when scannable 2D data.
kind: playbook
---

# Markdown Writing Practices

Application skill for Markdown style. For HTML/CSS page templates, load `frontend-markup-practices`. For platform wiki syntax (Confluence), use stack conventions.

## Core Principle

Documentation Markdown is **maintainable plain text**, one H1, wrapped prose, fenced code, descriptive links, minimal HTML.

## When to Use / NOT

- README, skills, ADRs, handbook pages, repo docs under `docs/` or `references/`.
- Reviewing doc PRs for structure and link hygiene.

**NOT when:**

- Generated API docs from source comments, validate generator templates.
- Rich wiki with non-Markdown macros only, use the platform’s own documentation.

## Workflow

1. **Layout**, H1, intro, TOC, headings, 80-col wrap.
2. **Lists & code**, lazy numbering, fences, languages.
3. **Links & media**, paths, reference links, alt text.
4. **Tables**, 2D data only; Markdown not HTML.
5. **Verify**, markdownlint/remark + `git diff --check` on changed `.md` files.

## Red Flags

- Multiple H1 or Setext headings
- `[here](url)` / bare URL link text
- `../../..` relative link chains
- Indented code blocks without language
- Trailing whitespace for line breaks
- HTML layout where Markdown suffices
- Tables that should be lists
- Images without alt text

## Verification

- markdownlint (or project remark config) on changed files
- `git diff --check` clean
- Render preview spot-check for TOC, fences, tables
