# MDN / Mozilla code examples style — learning note

**Status:** deep ingest (2026-08-28). **Feeds:** `mdn-style-*.md` capsules, `mdn-code-examples-practices` application skill.

## Sources read

| Source | What we extracted |
|---|---|
| [Guidelines for writing code examples](https://developer.mozilla.org/en-US/docs/MDN/Writing_guidelines/Code_style_guide) (primary) | Copy-paste-safe examples; Prettier; 15–25 lines; inclusive; lorem ipsum placeholders; correct fence language; `example-good`/`example-bad` |
| [JavaScript code examples](https://developer.mozilla.org/en-US/docs/MDN/Writing_guidelines/Code_style_guide/JavaScript) (primary) | Baseline modern JS; const/let; camelCase; braces; for...of; strict ===; template literals; textContent not innerHTML; comments `//` |
| [HTML code examples](https://developer.mozilla.org/en-US/docs/MDN/Writing_guidelines/Code_style_guide/HTML) (primary) | `<!doctype html>`; lang/charset/viewport; double-quoted attrs; lowercase; kebab-case classes; boolean attrs without value |
| [CSS code examples](https://developer.mozilla.org/en-US/docs/MDN/Writing_guidelines/Code_style_guide/CSS) (primary) | Vanilla CSS only; no BEM/Sass; class selectors; modern rgb(); range media queries; no !important; valid CSS in fences |
| [Writing style guide](https://developer.mozilla.org/en-US/docs/MDN/Writing_guidelines/Writing_style_guide) (secondary) | Pre/post example descriptions; live sample concatenation behavior |
| `javascript-coding-practices` / `frontend-markup-practices` (secondary) | App/repo JS/HTML — MDN rules target **documentation examples**, not all production code |

**Scope:** **MDN Web Docs** (and adapted Mozilla doc) **code examples** in articles, live samples, and reference pages. **Production app code:** use stack skills; borrow MDN patterns where they align.

## Mental model

MDN example quality is **copy-paste-safe teaching snippets** formatted consistently:

1. **General** — short, vanilla, runnable-minded, Prettier, inclusive text, correct fence language.
2. **JavaScript** — Baseline features; const/let; declarations over arrow assignment; braces; safe DOM APIs.
3. **HTML** — lowercase, semantic kebab classes, quoted attributes, complete-doc boilerplate when needed.
4. **CSS** — plain CSS, class selectors, modern color/media syntax, no preprocessors/methodologies in samples.

## Decision tables

### General (all languages)

| Topic | Rule |
|---|---|
| Purpose | understandable, reduced working examples; not clever production hacks |
| Dependencies | vanilla; no frameworks/preprocessors unless documenting them |
| Copy-paste | valid syntax; warn if snippet incomplete |
| Length | ~15–25 lines ideal; link out for full demos |
| Line wrap | no horizontal scroll; template literals over ugly concat |
| Formatting | Prettier (MDN config) — don't bike-shed indent |
| Language tag | correct fence language; `plain` for pseudocode; never wrong language for highlighting |
| Placeholders | lipsum.com standard lorem ipsum |
| Inclusive | diverse realistic names/contexts in examples |
| Deprecated | don't use `document.write`, presentation HTML for brevity |
| Browser lists | feature detection, not version comments in code |
| Live sample size | width 100%; height ≤700px recommended |
| Good/bad | `example-good` / `example-bad` on fences when contrasting |

### JavaScript (selected)

| Topic | Rule |
|---|---|
| Modern | Baseline-supported features in unrelated demos |
| Variables | `const` default; `let` if reassigned; never `var` |
| Names | camelCase functions; PascalCase classes; semantic 3–10 chars |
| Functions | `function` declarations; arrow for callbacks; not `const x = () =>` for named fns |
| Loops | `for...of` / `forEach`; not `for...in` on arrays; never omit loop `const`/`let` |
| Control | braces always; no `else` after `return`; switch case scopes |
| Equality | `===` / `!==`; `== null` only with comment |
| Strings | template literals for interpolation |
| Comments | `//` single-line; capital start; no period; ellipsis in comments |
| DOM | `textContent` not `innerHTML` for text; no `alert()`; appropriate `console.*` |
| APIs | no prefixes if Baseline; no deprecated XHR/ScriptProcessorNode |
| Async | prefer async/await; no top-level await unless ESM context clear |

### HTML (selected)

| Topic | Rule |
|---|---|
| Full docs | `<!doctype html>`, `lang`, `charset=utf-8`, viewport meta |
| Casing | lowercase elements/attributes |
| Attributes | double quotes; boolean attrs name-only (`required`) |
| Classes/ids | semantic kebab-case; not camelCase class names |
| Characters | literal Unicode over unnecessary entities |

### CSS (selected)

| Topic | Rule |
|---|---|
| Stack | vanilla CSS only — no Sass/Less/BEM/SMACSS in examples |
| Selectors | prefer classes; IDs for JS/anchors not styling |
| Syntax | well-formed CSS in `css` fences; pseudocode → `plain` or CSSSyntaxRaw |
| Colors | named when fine; else modern `rgb()` space syntax; `#aabbcc` hex |
| Media | range syntax `(width >= 480px)`; mobile-first ordering |
| Specificity | avoid !important; thoughtful cascade order |
| Units | relative units default (em/rem/%) over px |
| Keyframes | `from`/`to` when only endpoints |

## Anti-patterns

- Framework/BEM/bootstrap class names in generic examples
- Wrong markdown fence language (breaks Prettier/highlight)
- Invalid JS/CSS in copy-paste blocks (bare `…` in JS)
- `innerHTML` for plain text insertion
- `var`, loose `==`, `for...in` on arrays
- Browser prefix fallbacks when Baseline unprefixed
- Sass/Less/Stylus in MDN CSS blocks
- Non-well-formed CSS marked as `css`
- camelCase HTML class names (`bigRedBox`)
- Unquoted HTML attributes when examples teach clarity
- Keyword stuffing or browser version comments in example code
- Huge 100+ line blocks without external link
- Hungarian notation in JS examples

## Skill trace

| Artifact | Role |
|---|---|
| `mdn-style-examples-principles.md` | general, prettier, size, fences, inclusive |
| `mdn-style-javascript-examples.md` | JS patterns, DOM, comments, loops |
| `mdn-style-html-examples.md` | doctype, attrs, casing, semantics |
| `mdn-style-css-examples.md` | vanilla CSS, selectors, color, media |
| `mdn-code-examples-practices/SKILL.md` | MDN example review workflow |

## Relation to sibling skills

| MDN examples | App code skills |
|---|---|
| Short teaching snippets | Full module architecture |
| Prettier MDN config | Project ESLint/Prettier config |
| textContent in demos | App may use framework patterns |
| No BEM in examples | Project may use BEM internally |
| `javascript-coding-practices` | overlaps on const/===/braces — MDN adds doc-specific DOM/comment rules |
| `frontend-markup-practices` | overlaps on semantics — MDN adds doc boilerplate and kebab classes |
| `markdown-writing-practices` | MDN prose lives in writing style guide; this skill is **code blocks** |
