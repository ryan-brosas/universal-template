---
title: objc-coding-practices
summary: Use when authoring or reviewing Objective-C, Google/GitHub layout, 3+ char prefixes, property/copy semantics, designated initializers, Doxygen docs, NSError errors, literals, and clang-format/static analysis in CI.
kind: playbook
---

# Objective-C Coding Practices

Application skill for Objective-C style. Follow Apple Cocoa Coding Guidelines plus project `clang-format`; GitHub tab legacy trees normalize via formatter over time.

## Core Principle

Objective-C quality is **prefixed, documented headers with explicit ownership**, copy immutables, designated inits, NSError for expected failures.

## When to Use / NOT

- iOS/macOS ObjC and ObjC++ (`.m`, `.mm`) libraries and app code.
- Setting up clang-format, clang-tidy, OCLint, Xcode analyze in CI.

**NOT when:**

- Swift-only modules, use `swift-coding-practices`.
- Generated ObjC stubs, validate generators.

## Workflow

1. **Layout**, indent, braces, imports.
2. **Naming**, prefixes, categories.
3. **Memory**, properties, init, copy.
4. **Docs/errors**, Doxygen, NSError.
5. **Verify**, clang-format, analyzer, header doc audit on exports.

## Red Flags

- Two-letter class prefix
- Unprefixed category methods on shared types
- `getFoo` accessor naming
- Dot syntax on non-property methods
- Missing memory semantics on properties
- `@synthesize` without compiler requirement
- Iv ar access outside init/dealloc/custom accessor
- Messaging `self` in `-init`/`-dealloc` for overridable selectors
- `+new` usage
- Redundant ivar nil/zero initialization in init
- Individual Foundation subheaders instead of umbrella import
- `#include` on ObjC headers
- Unsigned down-count loops
- Macro constants where `static const` suffices
- Exceptions for normal control flow
- Undocumented public methods/properties
- Returning mutable where immutable contract promised
- No copy of mutable args in setters/async
- Weak long-lived references (refactor target)
- Mixed selector wrapping styles in one file
- Tomdoc/Doxygen missing nil documentation on object params

## Verification

- `clang-format --dry-run` / Xcode format on changed files
- `xcodebuild analyze` or project static analyzer
- Public header Doxygen/nil-contract audit
