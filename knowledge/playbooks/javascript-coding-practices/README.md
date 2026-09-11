---
title: javascript-coding-practices
summary: Use when authoring or reviewing JavaScript, named ES module exports, const/let, strict equality, semicolons and braces, trailing commas, arrow callbacks, JSDoc on public API, and banned eval/with/var.
kind: playbook
---

# JavaScript Coding Practices

Application skill for JavaScript style. For TypeScript domain rules, load `typescript-coding-standards`; for React, consult React's own source or docs.

## Core Principle

JavaScript maintainability is **explicit modules and lint-enforced habits**, named exports, const-by-default, strict equality, semicolons, no dynamic eval.

## When to Use / NOT

- `.js`/`.mjs` modules, Node/browser scripts, ESLint setup.
- Reviewing import/export boundaries or equality/truthiness bugs.

**NOT when:**

- TypeScript-only codebase, use `typescript-coding-practices` (style) and `typescript-coding-standards` (domain); still shares many ESLint rules with JS.
- Generated/bundled output, validate source instead.

## Workflow

1. **Modules**, named exports, immutable export surface, dedupe imports.
2. **Bindings**, `const`/`let`, `===`, explicit empty string/length checks.
3. **Format**, 2 spaces, semicolons, braces, trailing commas, switch `default`.
4. **Functions**, camelCase, arrows in callbacks, JSDoc on exports, ban eval/with/var.
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
