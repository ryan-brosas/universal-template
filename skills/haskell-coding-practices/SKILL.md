---
name: haskell-coding-practices
description: "Use when authoring or reviewing Haskell — 4-space/80-col layout, Haddock, explicit imports, type signatures, avoid partial functions, strict data, IO separation, and stylish-haskell/HLint/cabal test in CI."
disable-model-invocation: true
---

# Haskell Coding Practices

Application skill for Haskell style learning (from the archived `awesome-guidelines` style capsules). For GHC internals or specific linters (fourmolu vs stylish-haskell), follow project config first.

## Core Principle

Haskell quality is **explicit equational modules** — typed total functions in pure core, strict data by default, IO pushed to the rim.

## When to Use / NOT

- Haskell libraries, applications, and GHC-adjacent tools using Cabal/Stack.
- Setting up stylish-haskell/fourmolu, HLint, `-Wall -Werror`, Haddock in CI.

**NOT when:**

- Pure FFI C fragments — use C practice skills for foreign code.
- TH/splice-generated-only modules — validate generators.

## Workflow

1. **Layout** — indent, cols, case (`haskell-style-formatting-layout.md`).
2. **Modules** — names, imports, Haddock (`haskell-style-naming-imports.md`).
3. **Functions** — sigs, totality, guards (`haskell-style-functions-control.md`).
4. **Types/IO** — strict data, boundaries (`haskell-style-types-io.md`).
5. **Verify** — formatter, HLint, `cabal build`/`stack test`, Haddock on changed modules.

## Red Flags

- Tabs or trailing whitespace
- Lines >80 without strong reason
- Missing Haddock on exports
- Unqualified Map/Set imports
- Blanket imports without explicit list
- Missing top-level type signatures on exports
- `head`, `tail`, `fromJust` on untrusted input
- Brace-semicolon case layout
- Type synonyms for domain types
- Lazy record fields by default
- Pure/IO mixed without module seam
- `<- return` instead of `let`
- Lazy read+write same file
- Over-point-free unreadable code
- `-Wall` warnings ignored
- `String` in new public API
- Commented-out dead code
- Debug `trace` as user output

## Verification

- stylish-haskell / fourmolu (project config)
- HLint with project rules
- `cabal build --ghc-options=-Wall` or `-Werror` policy
- Haddock build for libraries
- Capsule checklist on export list + signatures

## Skill Result Contract

```xml
<skill_result>
  <skill>haskell-coding-practices</skill>
  <status>success|partial|blocked|failure</status>
  <artifacts>hs diff, format/HLint/build/Haddock output</artifacts>
  <evidence>learning note + capsule probes cited</evidence>
  <risks>partiality bug, space leak, IO ordering, or none</risks>
</skill_result>
```

## References

- `awesome-guidelines/references/haskell-style-learning-note.md`
- `awesome-guidelines/references/haskell-style-formatting-layout.md`
- `awesome-guidelines/references/haskell-style-naming-imports.md`
- `awesome-guidelines/references/haskell-style-functions-control.md`
- `awesome-guidelines/references/haskell-style-types-io.md`
