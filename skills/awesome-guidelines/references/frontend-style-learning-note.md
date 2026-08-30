# Frontend (HTML/CSS) — learning note

**Status:** deep ingest (2026-08-28). **Feeds:** `frontend-*.md` capsules, `frontend-markup-practices` application skill.

## Sources read

| Source | What we extracted |
|---|---|
| [Google HTML/CSS Style Guide](https://google.github.io/styleguide/htmlcssguide.html) | `<!doctype html>`, UTF-8, lowercase, semantics, alt text, separation of concerns, HTTPS assets, class over id, hyphenated classes, avoid `!important`, valid HTML/CSS |
| [CSS Guidelines](https://cssguidelin.es/) (Harry Roberts) | Selector intent, location independence, no IDs in CSS, `js-*` hooks separate from style classes, BEM-like naming, specificity discipline, proactive utility `!important` only |
| [HTML + CSS Code Guide](https://codeguide.co/) (Mark Otto) | Attribute order, boolean attrs, `.js-*` behavior classes, declaration grouping (position/box/type/visual), co-located media queries, avoid `@import`, meaningful class names, WCAG contrast note |

**Not duplicated here:** TypeScript/React/component frameworks — see `typescript-coding-standards`, `foundation-pack/react-foundation`, stack capsules in `foundation-pack/`.

## Mental model

Frontend markup/style guides converge on **separation of concerns** and **predictable selectors**:

1. **HTML** — structure + semantics + accessibility (correct element, meaningful `alt`, `lang`, valid doctype). Behavior and presentation leave the markup: no inline styles, no `div` buttons, prefer `<a>`/`<button>`.
2. **CSS** — classes describe purpose (not `.red`), hyphen-delimited, reusable across pages. Selectors are **explicit** (selector intent) and **low-specificity** (no `#id`, rarely qualify with element type). JavaScript hooks (`.js-*` or `data-*`) never share styling classes.
3. **Delivery** — UTF-8, HTTPS for assets, prefer `<link>` over `@import`, validate HTML/CSS baseline.

Conflicts between sources are **documented, not hidden** — projects pick via formatter/linter config; this catalog defaults to Google formatting + CSS Guidelines architecture + Code Guide component organization.

## Decision tables

### HTML semantics & a11y

| Case | Rule |
|---|---|
| Clickable navigation | `<a href>` not `<div onclick>` |
| Actions | `<button>` not styled `<div>` |
| Images | meaningful `alt`; decorative → `alt=""` |
| Document | `<!doctype html>`, `<meta charset="utf-8">`, `lang` on `<html>` |
| Entities | UTF-8 characters, not `&ldquo;` unless `<`/`&` |
| IDs | only when required; include hyphen if used (`user-profile`) |

### Separation of concerns

| Layer | Belongs in |
|---|---|
| Structure | HTML templates |
| Presentation | stylesheets |
| Behavior | scripts |
| Cross-link | minimal `<link>`/`<script>` tags |

### CSS naming & selectors

| Pattern | Verdict |
|---|---|
| Class names | lowercase, hyphen-separated, meaningful (`.tweet-header`) |
| Presentational | avoid `.red`, `.left` as primary API |
| IDs in CSS | avoid — use classes |
| Type qualifiers | avoid `ul.nav` unless necessary |
| Selector depth | ≤3 elements; explicit class over `header ul` |
| JS hooks | `.js-toggle` — not styled in CSS |

### Specificity & overrides

| Tool | When |
|---|---|
| More specific selector | preferred over `!important` |
| `!important` | avoid reactive fixes; rare proactive utilities (`.hidden`) |
| IDs in HTML/JS | OK; IDs in CSS — no |

### Formatting & organization (reconciled)

| Topic | Catalog default |
|---|---|
| Indent | 2 spaces, no tabs |
| Case | lowercase HTML/CSS |
| Declarations | group logically (position → box → type → visual) OR alphabetize — pick one per repo |
| Shorthand | use when setting all components intentionally; else explicit longhands (Code Guide) |
| Media queries | next to the rule they modify |
| `@import` | avoid — use `<link>` or build concat |
| Colors | `#fff` lowercase; prefer modern `rgb()` space syntax when supported |

### Source conflicts (pick per project)

| Topic | Google | Code Guide | Resolution |
|---|---|---|---|
| Optional closing tags | omit when safe | keep closers | formatter decides; document choice in project |
| Shorthand | prefer | limit to needed sides | explicit unless full shorthand intentional |
| Leading zero | `0.8em` | `.5` not `0.5` | align with Stylelint/Prettier config |
| Declaration order | alphabetical (optional) | grouped categories | grouped categories recommended for reviews |

## Anti-patterns

- Presentational class names tied to one page location (`.promo .btn`).
- Styling on `.js-*` or sharing one class for CSS + JS binding.
- `#content table` greedy selectors.
- Inline `style=""` and presentation in HTML.
- Protocol-relative `//cdn...` or HTTP assets on HTTPS pages.
- `@import` chains in production CSS.
- Reactive `!important` to win specificity wars.

## Skill trace

| Artifact | Role |
|---|---|
| `frontend-html-semantics-accessibility.md` | markup, a11y, separation |
| `frontend-css-naming-selectors.md` | classes, intent, js hooks |
| `frontend-css-structure-formatting.md` | format, order, media queries |
| `frontend-assets-delivery.md` | HTTPS, charset, @import, validation |
| `frontend-markup-practices` | application skill |
