---
name: swift-coding-practices
description: "Use when authoring or reviewing Swift, let/guard/optionals, explicit access, struct/final defaults, API naming fluency, argument labels, defaulted parameters, and documentation summaries."
disable-model-invocation: true
---

# Swift Coding Practices

Application skill for Swift style learning (from the archived `awesome-guidelines` style capsules). For SwiftUI/UIKit/SPM layout, load stack capsules in `foundation-pack/`.

## Core Principle

Swift readability is **clarity at the point of use**, safe bindings, fluent names, grammatical argument labels, documented declarations.

## When to Use / NOT

- Swift application/library/Package.swift modules, SwiftLint/SwiftFormat CI.
- Reviewing API names, labels, optionals, access control, docs.

**NOT when:**

- Non-Swift code.
- Generated Xcode project stubs, validate generators instead.
- Apple platform HIG-only UI, use platform foundation.

## Workflow

1. **Safety & access**, let, guard, optionals, struct/final (`swift-style-formatting-safety.md`).
2. **Naming**, roles, fluency, mutating pairs (`swift-style-naming-api.md`).
3. **Labels**, argument labels, defaults (`swift-style-argument-labels.md`).
4. **Docs & types**, summaries, methods vs functions (`swift-style-documentation-types.md`).
5. **Verify**, SwiftLint/SwiftFormat + `swift build` / `xcodebuild test` on changed targets.

## Red Flags

- Force-unwrap `!` / IUO `Type!`
- `var` when never mutated
- Redundant type words in names (`removeElement`)
- Missing `remove(at:)`-style label when needed
- Method family overloads instead of defaults
- Public API without `///` summary
- Non-final class without subclass plan
- Overload on return type only

## Verification

- SwiftLint/SwiftFormat on changed files
- Build + tests for touched modules
- Capsule checklist on public API review

## Skill Result Contract

```xml
<skill_result>
  <skill>swift-coding-practices</skill>
  <status>success|partial|blocked|failure</status>
  <artifacts>swift diff, lint/format output</artifacts>
  <evidence>learning note + capsule probes cited</evidence>
  <risks>force unwrap, ambiguous label, missing docs, or none</risks>
</skill_result>
```

## References

- `awesome-guidelines/references/swift-style-learning-note.md`
- `awesome-guidelines/references/swift-style-formatting-safety.md`
- `awesome-guidelines/references/swift-style-naming-api.md`
- `awesome-guidelines/references/swift-style-argument-labels.md`
- `awesome-guidelines/references/swift-style-documentation-types.md`
