---
name: nim-coding-practices
description: "Use when authoring or reviewing Nim, NEP-1 2-space/80-col layout, PascalCase/camelCase naming, init/new and abbrev API vocabulary, result-first procs, std/ imports, and --styleCheck plus tests in CI."
invocation: manual
disable-model-invocation: true
---

# Nim Coding Practices

Application skill for NEP-1 style learning (from the archived `awesome-guidelines` style capsules). For legacy codebases with non-NEP spellings, prefer `--styleCheck:usages` over full NEP-1 enforcement until migrated.

## Core Principle

Nim library quality is **guessable names + mechanical layout**, PascalCase types, camelCase API, `result` assignments, compiler styleCheck in CI.

## When to Use / NOT

- Nim packages, stdlib-shaped libraries, CLI/tools targeting NEP-1 conventions.
- Setting up `--styleCheck`, testament/`nim test`, nimble CI.

**NOT when:**

- Generated Nim from c2nim/other translators, validate generators.
- One-off scripts with local conventions, apply layout/naming lightly.

## Workflow

1. **Layout**, 2-space, 80 cols, multiline breaks (`nim-style-formatting-layout.md`).
2. **Naming/types**, PascalCase, enums, init/new (`nim-style-naming-types.md`).
3. **Procedures**, result, let, API verbs (`nim-style-procedures-api.md`).
4. **Modules/verify**, std imports, styleCheck (`nim-style-modules-verify.md`).
5. **Verify**, `nim c --styleCheck:error`, tests on changed modules.

## Red Flags

- Tab indentation
- Lines > 80 without wrap
- Manual column-aligned type blocks
- Shouting acronyms (`parseURL`)
- `existsFile` verbSubject order
- Unprefixed non-pure enum members
- `Exception` without CatchableError/Defect lineage
- `var` when value never reassigned
- Macro/template where proc suffices
- Terminal `return` instead of `result =`
- `getLen` / `append` instead of `len` / `add`
- Missing `m` prefix on mutating views
- `import os` without `std/` for stdlib
- Inconsistent identifier spelling across file
- Triple-quote content glued to opener line
- Unnecessary spaces in `a .. b`
- Undocumented exported procs

## Verification

- `nim c --styleCheck:error [--styleCheck:usages] <files>`
- Project test command (`nim test`, testament, nimble task)
- 80-column and 2-space spot check on changed hunks
- Capsule checklist on public API naming (`fileExists`, `initFoo`, `newFoo`)


## References

- `awesome-guidelines/references/nim-style-learning-note.md`
- `awesome-guidelines/references/nim-style-formatting-layout.md`
- `awesome-guidelines/references/nim-style-naming-types.md`
- `awesome-guidelines/references/nim-style-procedures-api.md`
- `awesome-guidelines/references/nim-style-modules-verify.md`
