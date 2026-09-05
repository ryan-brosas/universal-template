---
name: typescript-coding-practices
description: "Use when reviewing TypeScript style, modules, imports, nullability, or compiler/linter configuration; follow project conventions and consult Google TypeScript guidance as optional source-specific practice."
invocation: manual
disable-model-invocation: true
---

# TypeScript Style and Module Practices

For domain models, runtime validation, or failure semantics, select
`../typescript-coding-standards/SKILL.md`. For plain JavaScript, use
`../javascript-coding-practices/SKILL.md`. Review generated declarations through
their source or generator instead of hand-editing them.

Start with the project's TypeScript version, `tsconfig`, lint rules, framework,
and representative files. The archived Google-style capsules below are prior art,
not language restrictions. Apply them where adopted or where they close a named
gap; do not migrate a project's style during an unrelated change.

## Review the relevant surface

- **Modules:** choose imports and exports consistent with runtime resolution and
  packaging. Named exports and `import type` can clarify intent; default exports,
  CommonJS, or namespaces may be required by a framework or declaration format.
- **Types:** represent actual nullability and callback behavior. Prefer narrowing
  over unchecked assertions, but judge `any` at a compatibility boundary against
  the alternatives rather than hiding it with a cast. Nullable aliases and
  overloads are choices, not automatic defects.
- **Classes:** use `readonly`, parameter properties, `#private`, or TypeScript
  visibility according to runtime needs and project style. Check `const enum`
  against compilation and consumer constraints rather than banning it universally.
- **Verification:** run the project's typecheck and lint commands on the affected
  surface. Use `tsc --noEmit` only when appropriate for its build configuration.
  Check module output or a consuming build when resolution/export behavior changes.

## Focused source references

Load only a capsule relevant to the active question. These describe the source's
conventions; the project decides whether to adopt them.

- `../awesome-guidelines/references/typescript-style-learning-note.md`
- `../awesome-guidelines/references/typescript-style-modules-imports.md`
- `../awesome-guidelines/references/typescript-style-types-nullability.md`
- `../awesome-guidelines/references/typescript-style-classes-api.md`
- `../awesome-guidelines/references/typescript-style-verify.md`
