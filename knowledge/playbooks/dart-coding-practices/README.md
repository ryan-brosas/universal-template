---
title: dart-coding-practices
summary: Use when authoring or reviewing Dart, dart format, UpperCamelCase/lowerCamelCase naming, /// documentation, null-safe idioms, async/await, typed public API, class modifiers, and dart analyze/test in CI.
kind: playbook
---

# Dart Coding Practices

Application skill for Dart style. For Flutter UI patterns, consult the framework's own source or docs.

## Core Principle

Dart quality is **Effective Dart consistency**, formatted mechanically, documented publicly, null-safe and briefly expressed.

## When to Use / NOT

- Dart/Flutter libraries, CLI tools, server apps.
- Setting up `dart format`, `dart analyze`, `dart test`, linter rules in CI.

**NOT when:**

- Non-Dart code.
- Generated `.g.dart` / protobuf, validate generators.

## Workflow

1. **Format & names**, dart format, imports, casing.
2. **Docs**, `///` summaries, dart doc.
3. **Usage**, null, collections, async, errors.
4. **Design**, types, classes, equality.
5. **Verify**, `dart format`, `dart analyze`, `dart test` on changed packages.

## Red Flags

- Unformatted code
- Leading `_` on public symbols
- Missing docs on exported API
- Explicit `= null` initialization
- `.length == 0` emptiness checks
- Bare catch swallowing errors
- `new` keyword / redundant `const`
- Import from package `src/`
- Missing return type on public function
- Mutable class with custom `==`
- Positional boolean parameters

## Verification

- `dart format --set-exit-if-changed .`
- `dart analyze` (project strictness)
- `dart test` for changed packages
- `dart doc` or doc coverage review
