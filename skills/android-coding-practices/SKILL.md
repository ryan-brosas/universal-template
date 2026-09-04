---
name: android-coding-practices
description: "Use when authoring or reviewing Android apps, ribot/xmartlabs resource naming, component factories, Java/Kotlin conventions, MVP/Jetpack layering, and lint/detekt/tests in CI."
invocation: manual
disable-model-invocation: true
---

# Android Coding Practices

Application skill for ribot + Xmartlabs Android guides (archived `awesome-guidelines` capsules). For Kotlin syntax alone, load `kotlin-coding-practices`. Greenfield architecture: prefer Jetpack over legacy MVP/Rx verbatim.

## Core Principle

Android quality is **prefixed resources + factory-based navigation + layered UI/data**, not Activities that own network and database code.

## When to Use / NOT

- Android app modules, `res/` trees, Activities/Fragments/Compose screens, Gradle app projects.
- Reviewing layout naming, Intent keys, MVP/Repository boundaries, Espresso tests.

**NOT when:**

- Pure Kotlin/JVM libraries with no Android resources, `kotlin-coding-practices`.
- iOS/web clients.
- Generated R/layout binding boilerplate only, validate generators.

## Workflow

1. **Resources**, drawables, layouts, strings (`android-style-resources-layout.md`).
2. **Code**, imports, fields, logs, wrap (`android-style-code-conventions.md`).
3. **Components**, factories, keys, tests (`android-style-components-tests.md`).
4. **Architecture**, layers, lint/tests (`android-style-architecture-verify.md`).
5. **Verify**, `./gradlew lint`, unit/Espresso on changed flows.

## Red Flags

- Empty catch or generic `catch (Exception)`
- Wildcard imports
- Layout/drawable names without type prefixes
- Layout file not matching Activity/Fragment name
- String literals in `<string-array>` items
- Public Intent/Fragment keys without factory encapsulation
- Starting Activities with ad hoc Intent assembly at call sites
- Verbose/debug logs in release builds with PII
- Activity/Fragment calling API or DB directly
- Presenter holding View beyond lifecycle
- EventBus for single-screen events
- Multiple blank lines inside class body (xmartlabs)
- Nested unreadable ternary
- `I`-prefixed interface names (xmartlabs)
- Plural entity in list fragment class name
- Skipping lint/detekt on changed Android module

## Verification

- `./gradlew :app:lint` (or project lint task) on changed modules
- Unit tests (`*Test`) and Espresso (`*ActivityTest`) on touched screens
- Resource naming spot-check vs capsules
- Package boundary check: UI does not import data IO directly
- Capsule checklist on factory methods for new Activities/Fragments


## References

- `awesome-guidelines/references/android-style-learning-note.md`
- `awesome-guidelines/references/android-style-resources-layout.md`
- `awesome-guidelines/references/android-style-code-conventions.md`
- `awesome-guidelines/references/android-style-components-tests.md`
- `awesome-guidelines/references/android-style-architecture-verify.md`

## Related skills

- `kotlin-coding-practices`, Kotlin formatting/idioms
- `java-coding-practices`, JVM naming where shared
