---
title: swift-coding-practices
summary: Use when authoring or reviewing Swift, let/guard/optionals, explicit access, struct/final defaults, API naming fluency, argument labels, defaulted parameters, and documentation summaries.
kind: playbook
---

# Swift Coding Practices

Application skill for Swift style. For SwiftUI/UIKit/SPM layout, load the framework's own source or docs.

## Core Principle

Swift readability is **clarity at the point of use**, safe bindings, fluent names, grammatical argument labels, documented declarations.

## When to Use / NOT

- Swift application/library/Package.swift modules, SwiftLint/SwiftFormat CI.
- Reviewing API names, labels, optionals, access control, docs.

**NOT when:**

- Non-Swift code.
- Generated Xcode project stubs, validate generators instead.
- Apple platform HIG-only UI, follow Apple’s platform documentation.

## Workflow

1. **Safety & access**, let, guard, optionals, struct/final.
2. **Naming**, roles, fluency, mutating pairs.
3. **Labels**, argument labels, defaults.
4. **Docs & types**, summaries, methods vs functions.
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
