<!-- capsule-v2 -->
# Tables and portability — is Markdown used instead of HTML hacks?

**Source:** Google Markdown style guide §Tables, §Strongly prefer Markdown to HTML. **Question:** Are tables justified and is the corpus portable across renderers?

## Table vs list seam
**Path/Symbol:** tabular data in docs.
**Signature:** tables for uniform 2D scan data; lists otherwise.
**Data Shape:** reference links keep cells short.

### When to use a table
```markdown
Transport   | Favored by     | Advantages
----------- | -------------- | ---------------------------------
Swallow     | Coconuts       | Fast when unladen [airspeed]
Bicycle     | Miss Gulch     | Weatherproof [tornado]

[airspeed]: https://example.com/airspeed
[tornado]: https://example.com/tornado
```

**Flow:** table when many rows share parallel attributes across columns → reference links for long cell URLs → avoid sparse/wide tables with rambling prose cells.
**Invariant:** table used for data better shown as nested headings + bullets fails review.
**Probe:** "could this be a list?" review question; table column count ≤ readability budget.

## Anti-table example (prefer list)
```markdown
## Fruits

### Apple

* Juicy
* Firm

Apples keep doctors away.

### Banana

* Convenient
* Soft
```

**Flow:** switch to list + subheadings when columns repeat or dimensions unbalanced.
**Invariant:** single-column tables or mostly empty cells fail review.
**Probe:** rendered table scannable in <5 seconds.

## Markdown-not-HTML seam
```markdown
Use **bold** and `code` — not `<b>` or `<code>` unless renderer lacks support.

| Feature | Supported |
| ------- | --------- |
| Tables  | Yes       |
```

**Flow:** prefer CommonMark/GFM constructs → avoid HTML layout hacks → exception: rare host-required embeds documented in project guide.
**Invariant:** `<div>`, `<table>` HTML when native Markdown suffices fails review.
**Probe:** grep `<[a-z]` in `.md` diff; renderer portability check (Gitiles/GitHub/GitLab).

## Verdict
Tables only for true 2D data; reference links in cells; Markdown over HTML. Learning note: `markdown-style-learning-note.md`.
