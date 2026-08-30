<!-- capsule-v2 -->
# Formatting and layout — does Node JS match felixge 2-space/semicolon profile?

**Source:** felixge/node-style-guide §Formatting. **Question:** Are indent, semicolons, quotes, braces, and line length consistent with classic Node style?

## Layout seam
**Path/Symbol:** `.js`/`.mjs` Node application files.
**Signature:** 2-space indent; semicolons; 80 cols; single quotes; K&R braces.
**Data Shape:** `.editorconfig`; felixge `.jshintrc` or ESLint equivalent.

### Decisive pattern
```js
if (isValid) {
  doWork();
}

var keys = ['foo', 'bar'];
var values = [23, 42];
```

**Flow:** indent with **2 spaces** only — never mix tabs and spaces → use **semicolons** → limit lines to **80 characters** → use **LF** newlines with final newline at EOF → remove **trailing whitespace** → use **single quotes** for strings except JSON → place opening `{` on the **same line** as `if`/`for`/`function` → declare **one variable per var/let/const statement** (align `var` columns if grouping visually) → modern code: prefer `const`/`let` over legacy `var` unless project uses felixge JSHint profile verbatim → enforce via EditorConfig + ESLint/Prettier aligned to team choice.
**Invariant:** tab indent, missing semicolon ASI reliance, double-quoted strings (felixge profile), or Allman braces fail Node style review.
**Probe:** EditorConfig check; eslint semi/quotes/indent rules; `grep $'\t'`; line-length spot check.

## Verdict
2-space semicolon K&R layout, single quotes, one binding per declaration line. Learning note: `node-style-learning-note.md`.
