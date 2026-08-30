# Markdown style — learning note

**Status:** deep ingest (2026-08-28). **Feeds:** `markdown-style-*.md` capsules, `markdown-writing-practices` application skill.

## Sources read

| Source | What we extracted |
|---|---|
| [Google Markdown Style Guide](https://github.com/google/styleguide/blob/gh-pages/docguide/style.md) (primary) | readable/portable/maintainable; single H1; intro + `[TOC]`; 80-char wrap; ATX headings; lazy list numbering; 4-space nested lists; fenced code with language; reference links; explicit internal paths; informative link text; tables only when 2D data; prefer Markdown over HTML |
| [Markdown Style Guide (cirosantilli)](http://www.cirosantilli.com/markdown-style-guide/) (secondary) | readable and portable corpus — aligns with Google portability goal |
| GitLab Markdown Style Guide (secondary, catalog pointer) | team handbook conventions — defer to project renderer (GitLab/CommonMark) when hosting differs |

**Not duplicated here:** Full Google Developer Documentation Style Guide prose — link for title capitalization. Platform-specific extensions (Gitiles `[TOC]`, GitLab alerts) — document per host.

## Mental model

Markdown style in this catalog is **maintainable plain text that diffs like code**:

1. **Document shape** — one H1 title; short intro; optional `[TOC]` after intro; H2+ sections; `## See also` for extras.
2. **Source hygiene** — ~80-column wrap (exceptions: links, tables, headings, fences); no trailing whitespace; ATX `#` headings with spacing.
3. **Lists & code** — lazy `1.` for long lists; 4-space nested indent; fenced blocks with language; `\` for terminal line breaks when needed.
4. **Links & tables** — descriptive link phrases; reference links for long URLs; explicit paths not `../` hops; tables only for scannable 2D data; Markdown over HTML.

## Decision tables

### Document layout

| Element | Rule |
|---|---|
| Title | single `#` H1 matching filename |
| Intro | 1–3 sentences after title |
| TOC | `[TOC]` after intro, before first H2 (when host supports) |
| Sections | start at `##` |
| See also | misc links at bottom |

### Formatting

| Topic | Rule |
|---|---|
| Line length | ~80 chars (wrap prose) |
| Headings | ATX `#`; space after `#`; blank lines around |
| Heading names | unique, fully descriptive (anchor clarity) |
| Trailing WS | avoid; use `\` for hard breaks sparingly |
| Product names | preserve official capitalization (`Markdown`) |

### Lists

| Case | Rule |
|---|---|
| Long/mutable lists | lazy numbering (`1.` repeated) |
| Short stable lists | `1. 2. 3.` |
| Nested | 4-space text indent; 2 after number / 3 after bullet |
| Single-line items | one space after marker OK |

### Code

| Case | Rule |
|---|---|
| Inline | backticks for identifiers/commands |
| Blocks | fenced with language tag |
| In lists | indent fence to preserve list |
| Shell copy-paste | `\` at EOL for continued commands |

### Links & media

| Case | Rule |
|---|---|
| Internal | explicit path `/path/to/doc.md` |
| Relative | same-dir OK; avoid `../../` |
| Text | wrap meaningful phrase, not "here" |
| Long URLs | reference links; define after first use in section |
| Images | sparingly; always alt text |
| HTML | avoid except rare cases |

### Tables

| Case | Rule |
|---|---|
| Use when | uniform 2D scannable data |
| Avoid when | list + headings suffices |
| Long URLs in cells | reference link definitions |

## Anti-patterns

- Setext `---` under headings
- Multiple H1 per page
- `##Heading` without space
- Duplicate heading text (`### Summary` under Foo and Bar)
- Two trailing spaces for `<br>` (presubmit conflict)
- Indented code blocks without language
- `[here](url)` link text
- Raw duplicated long URLs in tables
- HTML hacks for layout
- Giant tables that should be lists

## Skill trace

| Artifact | Role |
|---|---|
| `markdown-style-document-layout.md` | H1, intro, TOC, 80 cols, headings |
| `markdown-style-lists-code.md` | lists, fences, language tags |
| `markdown-style-links-media.md` | paths, reference links, alt text |
| `markdown-style-tables-portability.md` | tables vs lists, Markdown not HTML |
| `markdown-writing-practices/SKILL.md` | markdownlint/remark in CI |
