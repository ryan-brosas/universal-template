---
name: linux-kernel-coding-practices
description: "Use when authoring or reviewing Linux kernel C — 8-tab indent, 80-col K&R braces, pointer-on-name spacing, descriptive globals, goto cleanup, kernel-doc, kmalloc_obj, and scripts/checkpatch.pl."
disable-model-invocation: true
---

# Linux Kernel C Coding Practices

Application skill for kernel coding-style (archived `awesome-guidelines` capsules). For GNU userspace C, load `gnu-c-coding-practices`. Generic portable C: `c-coding-practices`. Apache httpd: `httpd-c-coding-practices`.

## Core Principle

Kernel C quality is **checkpatch-clean tab layout and maintainable control flow** — 8-tab indent, 80 columns, descriptive global names, short functions, descriptive `goto` cleanup, kernel-doc on exports.

## When to Use / NOT

- Linux kernel in-tree or out-of-tree modules targeting upstream.
- Reviewing patches before `linux-kernel@vger.kernel.org` or maintainer lists.

**NOT when:**

- GNU userspace packages — `gnu-c-coding-practices`.
- Generic userspace C without kernel tree rules.
- Rust kernel code — Rust kernel docs (style guide is C-centric).

## Workflow

1. **Indent/braces** — tabs, 80 cols, switch alignment (`linux-kernel-style-indent-braces.md`).
2. **Naming/types** — pointers, typedefs, terminology (`linux-kernel-style-naming-types.md`).
3. **Functions/goto** — size, prototypes, cleanup (`linux-kernel-style-functions-goto.md`).
4. **Macros/verify** — kernel-doc, alloc, checkpatch (`linux-kernel-style-macros-verify.md`).
5. **Verify** — `./scripts/checkpatch.pl --strict` on changed files/patch; build + `make` targets for subsystem.

## Red Flags

- Spaces used for code indentation
- Lines >80 without strong readability reason
- Function `{` on same line as signature
- Double-indented `case` labels
- `char* p` or spaces inside `( )` in sizeof/calls
- Global/function named `foo` or `cntusr`
- New gratuitous `typedef struct ... foo_t`
- New master/slave or blacklist/whitelist without ABI/spec excuse
- Kitchen-sink function with many unrelated locals
- Missing parameter names in prototypes
- `EXPORT_SYMBOL` not immediately after function `}`
- `err:` label freeing nullable nested pointers
- Control-flow macro with hidden `return`
- `kmalloc(sizeof(struct x), ...)` decoupled from pointer var
- Cast on `kmalloc` return
- Broken/grep-hostile printk string wraps
- Exported API without kernel-doc update
- Skipping checkpatch on submitted patch

## Verification

- `./scripts/checkpatch.pl --strict --file <changed.c>` (or on `.patch`)
- Optional `scripts/Lindent` on touched C (separate cleanup commit if mass reformat)
- Subsystem `make` / `make CHECK=1` / `kselftest` as applicable
- Capsule probes on new gotos, exports, and alloc calls

## Skill Result Contract

```xml
<skill_result>
  <skill>linux-kernel-coding-practices</skill>
  <status>success|partial|blocked|failure</status>
  <artifacts>kernel patch/diff, checkpatch output</artifacts>
  <evidence>learning note + capsule probes cited</evidence>
  <risks>space indent, bad goto cleanup, or checkpatch failures</risks>
</skill_result>
```

## References

- `awesome-guidelines/references/linux-kernel-style-learning-note.md`
- `awesome-guidelines/references/linux-kernel-style-indent-braces.md`
- `awesome-guidelines/references/linux-kernel-style-naming-types.md`
- `awesome-guidelines/references/linux-kernel-style-functions-goto.md`
- `awesome-guidelines/references/linux-kernel-style-macros-verify.md`

## Related skills

- `c-coding-practices` — portable C safety baseline
- `gnu-c-coding-practices` — GNU userspace layout (not kernel tabs)
