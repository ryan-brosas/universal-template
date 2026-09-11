<!-- capsule-v2 -->
# JavaScript examples — does MDN JS match Baseline style, safe DOM, and comment rules?

**Source:** MDN JavaScript code style guide. **Question:** Are variables, control flow, loops, equality, and Web API usage aligned with MDN JS example rules?

## Variables and functions seam
**Path/Symbol:** ```js blocks in MDN docs.
**Signature:** const/let; camelCase; function declarations; strict ===.
**Data Shape:** Baseline features only in unrelated demos.

### Decisive pattern
```js
const visitedCities = [];

function sum(a, b) {
  return a + b;
}

for (const city of visitedCities) {
  console.log(city); // []
}
```

**Flow:** use Baseline-supported modern JS in unrelated examples → `const` unless reassigned; `let` then; never `var` → one declaration per line → camelCase functions/variables; PascalCase classes → prefer `function name(){}` over `const name = function` or arrow for named functions → arrow callbacks OK; implicit return when short → array/object literals not constructors → `push()` not `arr[arr.length] =` → `for...of`/`forEach` over C-style `for (;;)` on arrays; never `for...in` on arrays/strings → always `const`/`let` in loop headers → braces on all control flow → no `else` after `return` branch → switch: no break after return; brace case blocks when declaring locals → `===`/`!==`; `== null` only with comment → template literals for interpolation → explicit `Number()`/`String()` not `+`/`""+` coercion → try/catch recoverable errors only.
**Invariant:** `var`, loose equality, or unbraced one-line `for` fails MDN JS example review.
**Probe:** grep `var `, `==`, `for...in` in new js blocks.

## Comments and ellipsis seam
**Flow:** `//` single-line comments; space after slashes; capital start; no trailing period → comment intent not restate code → log output comment after `console.log` when helpful → multi-line via repeated `//`, not `/* */` → skip code with `// …` in comments, never bare unicode ellipsis in JS.
**Invariant:** block comments for ordinary narration or literal `…` in code body fails MDN JS comment rules.
**Probe:** scan comments and ellipsis patterns.

## Web API seam
**Flow:** no vendor prefixes when Baseline unprefixed → avoid deprecated APIs (fetch not XHR) → insert text with `textContent`, not `innerHTML` → static examples: `console.log`/`console.error`; live samples: UI output not `alert()` or invisible console → omit unused callback params with `/* , index */` when demonstrating.
**Invariant:** `innerHTML` for plain text or prefix soup in Baseline demo fails MDN safety review.
**Probe:** DOM insertion and fetch/XHR check in examples.

## Verdict
const/let, declarations, for...of, ===, template literals, // comments, textContent, Baseline APIs. Learning note: `mdn-style-learning-note.md`.
