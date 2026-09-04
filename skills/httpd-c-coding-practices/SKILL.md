---
name: httpd-c-coding-practices
description: "Use when authoring or reviewing Apache httpd C, 4-space 80-col layout, GNU indent profile, ANSI function/control-flow spacing, httpd cast rules, rationale comments, and build/tests in CI."
invocation: manual
disable-model-invocation: true
---

# Apache httpd C Coding Practices

Application skill for Apache httpd C style (archived `awesome-guidelines` capsules). For non-httpd portable C, load `c-coding-practices`. Kernel/GNU tab-based trees follow their own docs.

## Core Principle

httpd C quality is **reviewer-readable layout plus generic C safety**, ANSI signatures, httpd brace/spacing rhythm, 80-column wraps, comments for non-obvious rationale.

## When to Use / NOT

- Apache httpd core patches, httpd modules, APR-adjacent C matching httpd style.
- Reviewing layout before submitting to httpd dev list or ASF repo.

**NOT when:**

- Generic C libraries with no httpd contribution path, `c-coding-practices`.
- C++, `cpp-coding-practices`.

## Workflow

1. **Format**, indent, 80 cols, braces (`httpd-style-formatting-indent.md`).
2. **Functions/flow**, ANSI, if/switch (`httpd-style-functions-flow.md`).
3. **Expressions**, operators, casts, wraps (`httpd-style-expressions-casts.md`).
4. **Comments/verify**, rationale, build (`httpd-style-comments-verify.md`).
5. **Safety pass**, also apply `c-coding-practices` capsules for headers/errors/macros.

## Red Flags

- Tab characters
- Lines >80 without httpd-style wrap
- Old-style non-ANSI function definitions
- Space between function name and `(`
- Missing space after comma in calls
- Wrong `switch`/`case` indentation
- Space after cast `(int) j`
- Pointer cast `(char*)i` without space before `*`
- Comments that restate code instead of rationale
- Overlong functions without split plan
- Unchecked error returns (generic C safety)
- Data definitions in headers
- Layout-only fix mixed with logic in one commit

## Verification

- GNU indent with httpd flags on changed C (optional project step)
- `grep $'\t'` clean on touched files
- httpd/module build + relevant tests
- `-Wall`/project warning flags on changed translation units
- Capsule checklist on cast/flow samples


## References

- `awesome-guidelines/references/httpd-style-learning-note.md`
- `awesome-guidelines/references/httpd-style-formatting-indent.md`
- `awesome-guidelines/references/httpd-style-functions-flow.md`
- `awesome-guidelines/references/httpd-style-expressions-casts.md`
- `awesome-guidelines/references/httpd-style-comments-verify.md`

## Related skills

- `c-coding-practices`, portable C safety and headers
