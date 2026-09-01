---
name: mdn-code-examples-practices
description: "Use when authoring MDN/Mozilla doc code examples, Prettier, 15–25 line vanilla snippets, JS const/let/textContent, HTML5 lowercase kebab markup, modern vanilla CSS, and example-good/bad fences."
disable-model-invocation: true
---

# MDN Code Examples Practices

Application skill for MDN Web Docs code style hub (archived `awesome-guidelines` capsules). For application JS/HTML/CSS, load `javascript-coding-practices` and `frontend-markup-practices`. For repo Markdown structure, load `markdown-writing-practices`.

## Core Principle

MDN example quality is **copy-paste-safe teaching code**, short vanilla snippets, Prettier-formatted, Baseline-modern, with correct fence languages and MDN-specific DOM/CSS rules.

## When to Use / NOT

- MDN articles, reference pages, live samples, Mozilla doc porting aligned with MDN guides.
- Reviewing ```js/html/css``` blocks before mdn/content PR.

**NOT when:**

- Full application codebase, stack-specific practice skills.
- Prose/voice only, MDN Writing style guide + `mailchimp-content-practices`-adjacent tone docs.
- Shell session transcripts, MDN shell prompt guide (separate).

## Workflow

1. **Principles**, size, vanilla, fences, Prettier (`mdn-style-examples-principles.md`).
2. **JavaScript**, const/let, loops, DOM, comments (`mdn-style-javascript-examples.md`).
3. **HTML**, doctype, attrs, casing (`mdn-style-html-examples.md`).
4. **CSS**, vanilla, selectors, color/media (`mdn-style-css-examples.md`).
5. **Verify**, Prettier MDN config; correct fence language; `example-good`/`example-bad` when contrasting.

## Red Flags

- Framework/BEM/Bootstrap classes in generic examples
- Wrong ```language fence (similar-but-wrong language)
- Invalid JS/CSS (bare `…` in JS, non-well-formed css blocks)
- Snippet >25 lines without external full-example link
- `var`, loose `==`, `for...in` on arrays
- Unbraced one-line control flow
- `innerHTML` for plain text
- `alert()` in examples; wrong console usage in live vs static
- Vendor prefixes when Baseline unprefixed
- Sass/Less/BEM in CSS examples
- `!important` without strong reason
- camelCase HTML classes
- Unquoted HTML attributes in teaching markup
- Deprecated `document.write` / presentation HTML shortcuts
- Browser version lists in code comments
- Non-inclusive placeholder names/text

## Verification

- Prettier with MDN project config on changed examples
- Fence language matches block content (`plain` for pseudocode)
- Line-count and horizontal-scroll check
- Capsule probes on new JS DOM insertion and CSS validity
- Optional: MDN yari/build or repo lint scripts if present in target repo


## References

- `awesome-guidelines/references/mdn-style-learning-note.md`
- `awesome-guidelines/references/mdn-style-examples-principles.md`
- `awesome-guidelines/references/mdn-style-javascript-examples.md`
- `awesome-guidelines/references/mdn-style-html-examples.md`
- `awesome-guidelines/references/mdn-style-css-examples.md`

## Related skills

- `javascript-coding-practices`, app JS style
- `frontend-markup-practices`, semantic HTML/CSS in apps
- `markdown-writing-practices`, doc Markdown mechanics
