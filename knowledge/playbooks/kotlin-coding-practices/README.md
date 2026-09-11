---
title: kotlin-coding-practices
summary: Use when authoring or reviewing Kotlin, 4-space layout, PascalCase/camelCase naming, package-aligned files, class member order, val immutability, default parameters, expression if/when, and explicit library API.
kind: playbook
---

# Kotlin Coding Practices

Application skill for Kotlin style. For Android/Compose/KMP stack patterns, load the framework's own source or docs.

## Core Principle

Kotlin readability is **official formatter mechanics plus immutability-first idioms**, explicit imports, semantic class layout, stable library surfaces.

## When to Use / NOT

- Kotlin JVM/KMP/application/library source, ktlint/detekt CI.
- Reviewing naming, formatting, class organization, public API.

**NOT when:**

- Non-Kotlin code.
- Generated code, validate generators, not hand-edits.
- Compose/Android-only rules, load `android-coding-practices` when the stack is Android.

## Workflow

1. **Format & layout**, 4-space, braces, modifiers, trailing commas.
2. **Naming & files**, packages, files, constants, backing props.
3. **Organization**, directories, class layout, overloads.
4. **Idioms & API**, val, defaults, expression control flow, library KDoc.
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
