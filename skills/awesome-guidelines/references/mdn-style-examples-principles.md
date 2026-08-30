<!-- capsule-v2 -->
# Example principles — are snippets short, vanilla, copy-paste-safe, and Prettier-ready?

**Source:** MDN Code style guide (general). **Question:** Do examples teach one feature without unsafe or heavy dependencies, with correct fences and inclusive placeholders?

## Copy-paste safety seam
**Path/Symbol:** code blocks in MDN articles, live samples, reference pages.
**Signature:** valid syntax; 15–25 lines ideal; vanilla deps; warning if incomplete.
**Data Shape:** Prettier MDN config; correct ```language fence.

### Decisive pattern
```js
// Add your code here
// …
function createGreeting(name) {
  return `Hello, ${name}!`;
}
```

**Flow:** write examples readers may copy into production — usable, best-practice, not insecure/bloated/inaccessible → keep snippets short and focused on the immediate feature → prefer vanilla HTML/CSS/JS — no unnecessary server code, frameworks, preprocessors, or assumed library knowledge → use class names meaningful in the example, not BEM/Bootstrap-specific → include inclusive, diverse realistic text/names → avoid deprecated shortcuts (`document.write`, presentation elements) → if snippet is non-runnable or incomplete, warn in comment and prose → for not-yet-ubiquitous features in unrelated demos, use feature detection — don't embed browser version lists in comments → break long lines without horizontal scroll (template literals preferred over awkward concat) → aim ~15–25 lines; link to GitHub/Gist/CodePen for full demos → use standard lorem ipsum from lipsum.com for placeholder prose → run through Prettier with MDN config — don't debate manual indent → set fence language accurately; use `plain` for pseudocode/shell output — never a wrong language tag → optional `example-good` / `example-bad` after language for contrast blocks → live samples: ~100% width, height ≤700px when embedded.
**Invariant:** invalid syntax, framework-coupled generic demo, or missing language tag fails MDN example review.
**Probe:** Prettier check; fence language matches content; line count scan; copy-paste mental test.

## Inline code seam
**Flow:** mark function/method/variable names with inline code; methods include `()` — e.g. `doSomethingUseful()`.
**Invariant:** method name without parentheses in prose fails MDN inline convention.
**Probe:** spot-check prose markdown for `fn()` pattern.

## Verdict
Vanilla short valid examples, Prettier, correct fences, inclusive placeholders, external link for long demos. Learning note: `mdn-style-learning-note.md`.
