<!-- capsule-v2 -->
# HTML examples — does markup use HTML5 boilerplate, lowercase kebab semantics, and quoted attrs?

**Source:** MDN HTML code style guide. **Question:** Are full-document examples accessible-ready and snippets lowercase with double-quoted attributes?

## Document boilerplate seam
**Path/Symbol:** complete HTML examples and EmbedLiveSample snippets.
**Signature:** `<!doctype html>`; `lang`; UTF-8; viewport when full page.
**Data Shape:** lowercase throughout; double-quoted attributes.

### Decisive pattern
```html
<!doctype html>
<html lang="en-US">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width" />
    <title>Example document</title>
  </head>
  <body>
    <p class="editorial-summary">Lorem ipsum dolor sit amet.</p>
  </body>
</html>
```

**Flow:** for full documents use HTML5 doctype → set `lang` on `<html>` → `<meta charset="utf-8">` → include viewport meta for mobile-friendly live samples → snippets alone OK when macro supplies document wrapper → lowercase element and attribute names → double-quote all attribute values → boolean attributes name-only (`required`, not `required="required"`) → semantic kebab-case class/id names (`editorial-summary`, not `bigRedBox`) → prefer literal characters over unnecessary entities → Prettier for formatting.
**Invariant:** uppercase tags, unquoted multi-word attributes, or camelCase classes fail MDN HTML example review.
**Probe:** HTML validator mindset; attribute quote scan; class naming check.

## Prose about elements seam
**Flow:** in MDN prose use HTMLElement macro / `<code>` conventions for element and attribute names (per writing guide) — examples themselves stay lowercase literal HTML.
**Invariant:** shouting-case markup in example blocks fails consistency.
**Probe:** compare example block casing vs prose macro rules.

## Verdict
HTML5 doctype/lang/charset/viewport when full doc; lowercase; quoted attrs; kebab classes. Learning note: `mdn-style-learning-note.md`.
