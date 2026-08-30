---
name: racket-coding-practices
description: "Use when authoring or reviewing Racket — DrRacket indent, kebab-case naming, define/cond/for idioms, provide/contract-out modules, rackunit tests, and raco test in CI."
disable-model-invocation: true
---

# Racket Coding Practices

Application skill for official Racket style learning (from the archived `awesome-guidelines` style capsules). Scribble and Typed Racket files follow guide exceptions noted in upstream docs.

## Core Principle

Racket quality is **DrRacket-readable text + explicit module contracts** — kebab-case names, top-down provide sections, rackunit-guarded changes.

## When to Use / NOT

- `#lang racket` libraries, HtDP/2htdp teaching code, PLT-style packages.
- Setting up DrRacket indent, rackunit, `raco test`, contract-out in CI.

**NOT when:**

- Generated `.rkt` from macros/tools — validate generators.
- Scribble-only layout rules — see Scribble exceptions in official guide.

## Workflow

1. **Textual** — indent, parens, width (`racket-style-formatting-textual.md`).
2. **Naming/constructs** — kebab-case, define/cond/for (`racket-style-naming-constructs.md`).
3. **Modules** — provide, contracts, size (`racket-style-modules-contracts.md`).
4. **Testing** — rackunit, handlers (`racket-style-testing-verify.md`).
5. **Verify** — DrRacket indent-all, `raco test` on changed files.

## Red Flags

- Tab characters
- Lines >102 without wrap (no file-local waiver)
- C-style closing paren on own line mid-form
- DrRacket indent-all changes file
- camelCase or snake_case identifiers
- Underscores in regular names
- Context-only cryptic abbreviations
- Nested `if`/`begin` where `cond`/`match` fits
- Heavy nested `let` where internal `define` works
- Long unnamed `lambda` bodies
- Macro where function works
- `(provide (all-defined-out))`
- provide blocks scattered at file bottom
- Missing purpose comment on exports
- Module >1000 lines without split plan
- Function >> screen height without decomposition
- Missing `contract-out` on public ADT modules
- Catch-all `(lambda (_ #t) #t)` handlers
- Bare `exn?` handler catching breaks
- Manual parameter save/restore vs `parameterize`
- Graphical syntax boxes in `.rkt`
- Plural collection module names
- Magic numbers without named constants
- Bug fix without rackunit regression
- No `(module+ test …)` on nontrivial new module
- Trailing whitespace
- Missing EOF newline
- Single `;` where `;;` section comment expected
- Graphical comment boxes breaking plain-text editors

## Verification

- DrRacket "Indent All" leaves file unchanged (or documented exception at top)
- `raco test path/to/changed.rkt` (or package test suite)
- provide/contract-out audit on new exports
- Handler predicate precision review
- Capsule checklist on kebab-case + top-down module layout

## Skill Result Contract

```xml
<skill_result>
  <skill>racket-coding-practices</skill>
  <status>success|partial|blocked|failure</status>
  <artifacts>rkt diff, raco test/indent output</artifacts>
  <evidence>learning note + capsule probes cited</evidence>
  <risks>contract gap, indent drift, swallowed exception, or none</risks>
</skill_result>
```

## References

- `awesome-guidelines/references/racket-style-learning-note.md`
- `awesome-guidelines/references/racket-style-formatting-textual.md`
- `awesome-guidelines/references/racket-style-naming-constructs.md`
- `awesome-guidelines/references/racket-style-modules-contracts.md`
- `awesome-guidelines/references/racket-style-testing-verify.md`
