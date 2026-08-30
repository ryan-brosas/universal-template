---
name: c-coding-practices
description: "Use when authoring or reviewing C, snake_case naming, header guards, no data in headers, Yoda comparisons, safe macros, initialize-all, and checked error returns."
disable-model-invocation: true
---

# C Coding Practices

Application skill for C style learning (from the archived `awesome-guidelines` style capsules). For Linux kernel or GNU projects, follow tree-specific style (tabs, 80 cols) when documented locally.

## Core Principle

C quality is **explicit scope, explicit control flow, explicit failures**, the language will not save you from unclear names or unchecked returns.

## When to Use / NOT

- C libraries, firmware, native extensions, syscall glue.
- Setting up clang-format, cppcheck, sparse, or static analysis in CI.

**NOT when:**

- C++ translation units, use `cpp-coding-practices`.
- Generated bindings, validate generator output.

## Workflow

1. **Format & control**, K&R braces, Yoda `==`, switch default (`c-style-formatting-control.md`).
2. **Naming**, snake_case, `g_`, pointers (`c-style-naming-types.md`).
3. **Headers**, guards, extern/define split (`c-style-headers-modules.md`).
4. **Macros & safety**, parenthesized macros, init-all, error checks (`c-style-macros-safety.md`).
5. **Verify**, compiler warnings (`-Wall -Wextra`), static analyzer on changed files.

## Red Flags

- Uninitialized variables
- Variable definitions in `.h`
- `char* a, b` declarations
- Macros without parenthesized parameters
- Magic numbers in conditionals
- Unchecked `malloc`/`fopen`/syscall returns
- `#ifdef DEBUG` without defined value semantics
- Abbreviated global names

## Verification

- `clang -Wall -Wextra -Werror` (project policy)
- cppcheck / Coverity / sparse on changed TUs
- Link test: header included from multiple `.c` files without duplicate symbols
- Capsule checklist on review

## Skill Result Contract

```xml
<skill_result>
  <skill>c-coding-practices</skill>
  <status>success|partial|blocked|failure</status>
  <artifacts>c/h diff, warning/analyzer output</artifacts>
  <evidence>learning note + capsule probes cited</evidence>
  <risks>unchecked error, header ODR, macro side effect, or none</risks>
</skill_result>
```

## References

- `awesome-guidelines/references/c-style-learning-note.md`
- `awesome-guidelines/references/c-style-formatting-control.md`
- `awesome-guidelines/references/c-style-naming-types.md`
- `awesome-guidelines/references/c-style-headers-modules.md`
- `awesome-guidelines/references/c-style-macros-safety.md`
