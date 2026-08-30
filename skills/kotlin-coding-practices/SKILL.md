---
name: kotlin-coding-practices
description: "Use when authoring or reviewing Kotlin, 4-space layout, PascalCase/camelCase naming, package-aligned files, class member order, val immutability, default parameters, expression if/when, and explicit library API."
disable-model-invocation: true
---

# Kotlin Coding Practices

Application skill for Kotlin style learning (from the archived `awesome-guidelines` style capsules). For Android/Compose/KMP stack patterns, load stack capsules in `foundation-pack/`.

## Core Principle

Kotlin readability is **official formatter mechanics plus immutability-first idioms**, explicit imports, semantic class layout, stable library surfaces.

## When to Use / NOT

- Kotlin JVM/KMP/application/library source, ktlint/detekt CI.
- Reviewing naming, formatting, class organization, public API.

**NOT when:**

- Non-Kotlin code.
- Generated code, validate generators, not hand-edits.
- Compose/Android-only rules, use Android style guide / foundation when stack is Android.

## Workflow

1. **Format & layout**, 4-space, braces, modifiers, trailing commas (`kotlin-style-formatting-layout.md`).
2. **Naming & files**, packages, files, constants, backing props (`kotlin-style-naming-files.md`).
3. **Organization**, directories, class layout, overloads (`kotlin-style-organization-classes.md`).
4. **Idioms & API**, val, defaults, expression control flow, library KDoc (`kotlin-style-idioms-api.md`).
5. **Verify**, ktlint/detekt + `./gradlew check` (or project equivalent) on changed modules.

## Red Flags

- Wildcard imports
- Tabs or inconsistent indent
- `var` when never reassigned
- Mutable collection types in public API parameters
- Overloads instead of default parameters
- `Util.kt` / meaningless file names
- Binary `when` instead of `if`
- Public API without return types (libraries)

## Verification

- ktlint/detekt on changed files
- Compile + tests for touched modules
- Capsule checklist on public API review

## Skill Result Contract

```xml
<skill_result>
  <skill>kotlin-coding-practices</skill>
  <status>success|partial|blocked|failure</status>
  <artifacts>kotlin diff, ktlint/detekt output</artifacts>
  <evidence>learning note + capsule probes cited</evidence>
  <risks>wildcard import, mutable API surface, missing library types, or none</risks>
</skill_result>
```

## References

- `awesome-guidelines/references/kotlin-style-learning-note.md`
- `awesome-guidelines/references/kotlin-style-formatting-layout.md`
- `awesome-guidelines/references/kotlin-style-naming-files.md`
- `awesome-guidelines/references/kotlin-style-organization-classes.md`
- `awesome-guidelines/references/kotlin-style-idioms-api.md`
