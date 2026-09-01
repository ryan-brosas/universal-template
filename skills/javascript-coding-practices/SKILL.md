---
name: javascript-coding-practices
description: "Use when authoring or reviewing JavaScript, named ES module exports, const/let, strict equality, semicolons and braces, trailing commas, arrow callbacks, JSDoc on public API, and banned eval/with/var."
disable-model-invocation: true
---

# JavaScript Coding Practices

Application skill for JavaScript style learning (from the archived `awesome-guidelines` style capsules). For TypeScript domain rules, load `typescript-coding-standards`; for React, `foundation-pack/react-foundation`.

## Core Principle

JavaScript maintainability is **explicit modules and lint-enforced habits**, named exports, const-by-default, strict equality, semicolons, no dynamic eval.

## When to Use / NOT

- `.js`/`.mjs` modules, Node/browser scripts, ESLint setup.
- Reviewing import/export boundaries or equality/truthiness bugs.

**NOT when:**

- TypeScript-only codebase, use `typescript-coding-practices` (style) and `typescript-coding-standards` (domain); still shares many ESLint rules with JS.
- Generated/bundled output, validate source instead.

## Workflow

1. **Modules**, named exports, immutable export surface, dedupe imports (`javascript-style-modules-exports.md`).
2. **Bindings**, `const`/`let`, `===`, explicit empty string/length checks (`javascript-style-variables-equality.md`).
3. **Format**, 2 spaces, semicolons, braces, trailing commas, switch `default` (`javascript-style-formatting-control.md`).
4. **Functions**, camelCase, arrows in callbacks, JSDoc on exports, ban eval/with/var (`javascript-style-functions-disallowed.md`).
5. **Verify**, eslint + formatter on changed paths.

## Red Flags

- `export default` without documented project exception
- `export let` mutated externally
- `var`, bare `except`-style loose equality (`== 0`)
- Missing semicolon before `(async function` IIFE
- `eval` / `new String()`

## Verification

- `eslint` (project config) exit 0 on changed files
- Prettier/clang-format check if configured
- Capsule checklist on review


## References

- `awesome-guidelines/references/javascript-style-learning-note.md`
- `awesome-guidelines/references/javascript-style-modules-exports.md`
- `awesome-guidelines/references/javascript-style-variables-equality.md`
- `awesome-guidelines/references/javascript-style-formatting-control.md`
- `awesome-guidelines/references/javascript-style-functions-disallowed.md`
