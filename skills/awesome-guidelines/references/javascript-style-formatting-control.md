<!-- capsule-v2 -->
# Formatting and control — will formatters and ASI agree?

**Source:** Google jsguide §4; Airbnb §Semicolons, §Blocks. **Question:** Is layout mechanically enforceable and are control structures unambiguous?

## Format seam
**Path/Symbol:** statements, literals, blocks.
**Signature:** 2-space indent; 80-column target; semicolon-terminated statements.
**Data Shape:** trailing commas in multiline `[`/`{`; K&R braces.

### Decisive patterns
```javascript
const config = {
  host: 'localhost',
  port: 8080,
};

if (short()) foo();

if (longCondition(a, b)) {
  doWork();
} else {
  cleanup();
}

switch (mode) {
  case 'a':
    handleA();
    break;
  default:
    handleDefault();
}
```

**Flow:** clang-format/Prettier/ESLint enforce base layout → always semicolon → braces on multi-line control → `default` last in switch.
**Invariant:** ASI must never be relied on for `[`/`(`/template continuations — terminate prior statement explicitly.
**Probe:** `semi` rule pass; formatter check clean; no single-line `for`/`while` without braces unless Google one-line `if` exception.

## Braces seam
**Flow:** every multi-statement branch uses `{}` → empty blocks may be `{}` on one line → exception: one-line `if` without `else` when readable.
**Invariant:** never `if (x) doSomething();` spanning wrap that hides else binding mistakes on review — prefer braces when wrapped.
**Probe:** eslint `curly` / `brace-style` per project config.

## Verdict
Adopt 2-space + semicolons + braces + trailing commas; project formatter wins column limit. Learning note: `javascript-style-learning-note.md`.
