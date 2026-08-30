<!-- capsule-v2 -->
# CSS naming and selectors — will this style leak or break JS hooks?

**Source:** Google HTML/CSS §Class Naming; CSS Guidelines §Selector Intent, §IDs, §JavaScript Hooks. **Question:** Can this component move to another page without rewriting CSS?

## Naming seam
**Path/Symbol:** `.component-name` class tokens.
**Signature:** lowercase, hyphen-delimited, purpose not presentation.
**Data Shape:** reusable classes; optional app prefix (`adw-`, `maia-`) in large codebases.

### Decisive contrast
```css
/* Wrong */
.button-green {}
#example {}
header ul {}

/* Right */
.btn {}
.site-nav {}
.tweet-header {}
```

**Flow:** name by purpose → single class per component surface → avoid IDs/type qualifiers in CSS → keep selectors ≤3 elements deep.
**Invariant:** **selector intent** — style exactly what you mean; greedy selectors (`header ul`, `#content table`) create override debt.
**Probe:** no `#` selectors in stylesheets; Stylelint max nesting depth; classes not tied to single page wrapper unless prefixed scope is intentional.

## JS hook seam
```html
<button class="btn btn-primary js-save">Save</button>
```
**Flow:** style `.btn*` in CSS → bind behavior to `.js-*` or `data-*` in JS → never remove/refactor CSS and break JS accidentally.
**Invariant:** one class must not be both the styling API and the JS query hook.
**Probe:** grep `.js-` in CSS files returns empty; JS queries use `js-*`/`data-*`, not styled classes alone.

## Verdict
Adopt meaningful hyphenated classes, explicit intent, no ID selectors; separate JS hooks. Learning note: `frontend-style-learning-note.md`.
