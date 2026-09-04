---
name: cpp-coding-practices
description: "Use when authoring or reviewing C++, self-contained headers, IWYU, PascalCase/snake_case naming, unique_ptr ownership, RAII, explicit conversions, and clang-format/cpplint in CI."
invocation: manual
disable-model-invocation: true
---

# C++ Coding Practices

Application skill for C++ style learning (from the archived `awesome-guidelines` style capsules). When project uses LLVM/Chromium/Mozilla variants, follow local baseline first.

## Core Principle

C++ quality is **header discipline + explicit ownership + readable names**, power features only when the call site stays obvious to the next reader.

## When to Use / NOT

- C++ libraries, services, native extensions, performance-critical code.
- Setting up clang-format, IWYU, cpplint, clang-tidy in CI.

**NOT when:**

- C code, use C-specific guides when ingested.
- Generated protobuf/grpc stubs, validate generators, not hand-edits.

## Workflow

1. **Headers & format**, guards, IWYU, 2-space layout (`cpp-style-formatting-headers.md`).
2. **Naming**, PascalCase types/functions, snake_case data, `k` constants (`cpp-style-naming-types.md`).
3. **Ownership**, `unique_ptr`, RAII, no naked new/delete (`cpp-style-ownership-raii.md`).
4. **Classes/API**, explicit ctors, struct vs class, short functions (`cpp-style-classes-api.md`).
5. **Verify**, clang-format, IWYU, cpplint/clang-tidy on changed translation units.

## Red Flags

- Transitive include dependence
- Raw owning pointer parameters
- Virtual calls from constructors
- Implicit conversion constructors
- `-inl.h` client-visible template splits
- camelCase locals in Google-style trees
- Returning reference/pointer to local

## Verification

- `clang-format --dry-run` / project formatter check
- IWYU fix or include-fixer clean
- cpplint / clang-tidy on changed files
- Capsule checklist on API review


## References

- `awesome-guidelines/references/cpp-style-learning-note.md`
- `awesome-guidelines/references/cpp-style-formatting-headers.md`
- `awesome-guidelines/references/cpp-style-naming-types.md`
- `awesome-guidelines/references/cpp-style-ownership-raii.md`
- `awesome-guidelines/references/cpp-style-classes-api.md`
