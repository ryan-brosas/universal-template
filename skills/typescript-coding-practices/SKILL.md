---
name: typescript-coding-practices
description: "Use when authoring or reviewing TypeScript style, named ES module exports, import type, unknown over any, nullable-at-use-site, optional params over overload sprawl, readonly/parameter properties, and banned default exports/namespaces/const enum."
disable-model-invocation: true
---

# TypeScript Coding Practices

Application skill for TypeScript **style and module** learning (from the archived `awesome-guidelines` style capsules). For domain modeling, branded types, and schema boundaries, load `typescript-coding-standards`; for plain JS, `javascript-coding-practices`.

## Core Principle

TypeScript maintainability is **typed modules with honest nullability**, named exports, `import type`, `unknown` at boundaries, no nullable aliases, minimal assertions.

## When to Use / NOT

- `.ts`/`.tsx` source, ESLint + `tsc` setup, import/export review.
- Callback/overload cleanup, class visibility/readonly habits.

**NOT when:**

- Domain architecture, Effect/Result, schema parsing, `typescript-coding-standards`.
- Generated `.d.ts` or bundled output, validate source instead.

## Workflow

1. **Modules**, named exports, `import type`, no namespaces/require, dedupe imports (`typescript-style-modules-imports.md`).
2. **Types**, primitives lowercase, `unknown` not `any`, null at use site, optional params (`typescript-style-types-nullability.md`).
3. **Classes**, parameter properties, `readonly`, no `#private`/`const enum`, rare `as` (`typescript-style-classes-api.md`).
4. **Verify**, `tsc --noEmit` + eslint on changed paths (`typescript-style-verify.md`).
5. **Domain pass**, when handling untrusted input or errors-as-data, also run `typescript-coding-standards`.

## Red Flags

- `export default` without documented exception
- `export let` mutated externally
- `namespace`, `import = require`, `/// <reference>`
- `type Foo = Bar | null` in shared aliases
- `catch (e: any)` or `(x: () => any)` callbacks
- `#private` fields or `const enum` without migration note
- Nullable alias re-exported across modules

## Verification

- `tsc --noEmit` exit 0 on project or changed files
- ESLint (`@typescript-eslint/no-explicit-any`, `no-non-null-assertion`, import rules) on changed paths
- Capsule checklist in `typescript-style-verify.md`


## References

- `awesome-guidelines/references/typescript-style-learning-note.md`
- `awesome-guidelines/references/typescript-style-modules-imports.md`
- `awesome-guidelines/references/typescript-style-types-nullability.md`
- `awesome-guidelines/references/typescript-style-classes-api.md`
- `awesome-guidelines/references/typescript-style-verify.md`
