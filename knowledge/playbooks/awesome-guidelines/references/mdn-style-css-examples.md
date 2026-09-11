<!-- capsule-v2 -->
# CSS examples — is CSS vanilla, valid, class-based, and modern-syntax?

**Source:** MDN CSS code style guide. **Question:** Do examples avoid preprocessors/methodologies, use well-formed CSS, and follow MDN color/media/selector rules?

## Vanilla CSS seam
**Path/Symbol:** ```css blocks in MDN docs.
**Signature:** no Sass/BEM; class selectors; valid declarations in css fences.
**Data Shape:** Prettier; Baseline modern features in unrelated demos.

### Decisive pattern
```css
.footnote {
  margin: 0.5em 1em;
  color: rgb(31 41 59);
}

@media (width >= 480px) {
  .footnote {
    max-width: 50%;
  }
}
```

**Flow:** document vanilla CSS only — no Sass/Less/Stylus, BEM/SMACSS naming, or CSS resets in generic examples → plan styles to minimize override wars → use Baseline modern features in unrelated demos → only well-formed CSS inside `css` fences; formal-syntax placeholders → `plain` or CSSSyntaxRaw macro → every css block needs property:value pairs (not bare function calls except Syntax section rules) → prefer class selectors; reserve IDs for JS/anchors → lowercase identifiers; kebab-case custom names → avoid `!important` except last resort → order higher-specificity rules later → use shorthand when all components set; canonical shorthand order → modern color `rgb(31 41 59 / 0.26)` not legacy comma rgba → prefer named colors when palette irrelevant → hex `#aabbcc` six-digit → relative units (em/rem/%) default over px → range media query syntax `(width >= 480px)`; mobile-first sheet ordering → double quotes in CSS strings/@import paths → `from`/`to` keyframes when only endpoints → `/* comment */` with space after asterisk on own lines above rules.
**Invariant:** preprocessor syntax, invalid css fence content, or ID-heavy styling in generic demo fails MDN CSS review.
**Probe:** grep `@mixin`, `$`, BEM `--`; validate css blocks parse; !important scan.

## Selector and specificity seam
**Flow:** use `:is()`/`:not()` complex lists to shorten selectors → pseudo-elements `::before` not `:before` → empty lines between declaration blocks when helpful.
**Invariant:** single-colon pseudo-element syntax in new examples fails MDN CSS guide.
**Probe:** `::` vs `:` spot-check on pseudo-elements.

## Verdict
Vanilla class-based CSS, valid fences, modern rgb/media syntax, no preprocessors. Learning note: `mdn-style-learning-note.md`.
