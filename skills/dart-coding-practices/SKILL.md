---
name: dart-coding-practices
description: "Use when authoring or reviewing Dart — dart format, UpperCamelCase/lowerCamelCase naming, /// documentation, null-safe idioms, async/await, typed public API, class modifiers, and dart analyze/test in CI."
disable-model-invocation: true
---

# Dart Coding Practices

Application skill for Dart style learning (`awesome-guidelines` deep ingest). For Flutter UI patterns, combine with stack-specific foundations.

## Core Principle

Dart quality is **Effective Dart consistency** — formatted mechanically, documented publicly, null-safe and briefly expressed.

## When to Use / NOT

- Dart/Flutter libraries, CLI tools, server apps.
- Setting up `dart format`, `dart analyze`, `dart test`, linter rules in CI.

**NOT when:**

- Non-Dart code.
- Generated `.g.dart` / protobuf — validate generators.

## Workflow

1. **Format & names** — dart format, imports, casing (`dart-style-formatting-names.md`).
2. **Docs** — `///` summaries, dart doc (`dart-style-documentation.md`).
3. **Usage** — null, collections, async, errors (`dart-style-usage-idioms.md`).
4. **Design** — types, classes, equality (`dart-style-design-api.md`).
5. **Verify** — `dart format`, `dart analyze`, `dart test` on changed packages.

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
- Capsule checklist on public API

## Skill Result Contract

```xml
<skill_result>
  <skill>dart-coding-practices</skill>
  <status>success|partial|blocked|failure</status>
  <artifacts>dart diff, analyze/test output</artifacts>
  <evidence>learning note + capsule probes cited</evidence>
  <risks>null unsafety, doc drift, API extendability leak, or none</risks>
</skill_result>
```

## References

- `awesome-guidelines/references/dart-style-learning-note.md`
- `awesome-guidelines/references/dart-style-formatting-names.md`
- `awesome-guidelines/references/dart-style-documentation.md`
- `awesome-guidelines/references/dart-style-usage-idioms.md`
- `awesome-guidelines/references/dart-style-design-api.md`
