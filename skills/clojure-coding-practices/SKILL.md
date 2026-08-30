---
name: clojure-coding-practices
description: "Use when authoring or reviewing Clojure — 2-space layout, gathered parens, sorted ns requires, lisp-case naming, ?/! conventions, threading idioms, keyword maps, ex-info errors, and clj-kondo/cljfmt in CI."
disable-model-invocation: true
---

# Clojure Coding Practices

Application skill for Clojure style learning (`awesome-guidelines` deep ingest). For ClojureScript-specific tooling, follow project `shadow-cljs` / `cljs` conventions.

## Core Principle

Clojure readability is **consistent layout + idiomatic expressions** — namespaces explicit, names conventional, data as maps/vectors, side effects marked.

## When to Use / NOT

- Clojure/ClojureScript application and library code.
- Setting up clj-kondo, cljfmt, clojure.test in CI.

**NOT when:**

- Non-Clojure code.
- Generated `cljs` from macros — validate generator output.

## Workflow

1. **Layout & ns** — indent, parens, `ns` hygiene (`clojure-style-layout-namespaces.md`).
2. **Naming** — lisp-case, `?`, `!`, dynamics (`clojure-style-naming-types.md`).
3. **Functions** — when/if-let, threading, arity (`clojure-style-functions-idioms.md`).
4. **Data & safety** — collections, errors, macros (`clojure-style-data-safety.md`).
5. **Verify** — cljfmt, clj-kondo, `clojure -M:test` on changed namespaces.

## Red Flags

- `:use` or `:refer :all`
- Single-segment library namespace
- camelCase/snake_case function names
- `def` inside function for local state
- Shadowing `clojure.core` without exclude
- List literals for sequential app data
- Index-based collection loops
- Catching `Throwable`
- Macro where function suffices
- Missing docstring on public API

## Verification

- `cljfmt check` / project formatter
- `clj-kondo --lint` on changed paths
- `clojure -M:test` or `lein test` / `bb test`
- Capsule checklist on namespace review

## Skill Result Contract

```xml
<skill_result>
  <skill>clojure-coding-practices</skill>
  <status>success|partial|blocked|failure</status>
  <artifacts>clj diff, fmt/lint/test output</artifacts>
  <evidence>learning note + capsule probes cited</evidence>
  <risks>ns collision, shadowed core, leaky macro, or none</risks>
</skill_result>
```

## References

- `awesome-guidelines/references/clojure-style-learning-note.md`
- `awesome-guidelines/references/clojure-style-layout-namespaces.md`
- `awesome-guidelines/references/clojure-style-naming-types.md`
- `awesome-guidelines/references/clojure-style-functions-idioms.md`
- `awesome-guidelines/references/clojure-style-data-safety.md`
