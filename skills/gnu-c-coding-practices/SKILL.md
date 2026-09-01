---
name: gnu-c-coding-practices
description: "Use when authoring or reviewing GNU package C, 79-col defun braces, GNU indent spacing, lowercase_with_underscores naming, English comments, braced nested if/else, Gnulib/Autoconf, and checked syscalls/malloc."
disable-model-invocation: true
---

# GNU C Coding Practices

Application skill for GNU Coding Standards (archived `awesome-guidelines` capsules). For generic portable C without GNU layout, load `c-coding-practices`. Apache httpd: `httpd-c-coding-practices`. Linux kernel: kernel coding-style, not this skill.

## Core Principle

GNU C quality is **tool-friendly layout plus explicit documentation and checked system behavior**, defun column-1 braces, spaces before `(`, semantic names, annotated `#endif`, Autoconf/Gnulib portability.

## When to Use / NOT

- GNU packages (coreutils, binutils, emacs, gnulib-using trees), FSF contribution paths.
- Reviewing C before merge to Savannah/FSF-maintained repos.

**NOT when:**

- Linux kernel C, kernel coding-style (tabs, different rules).
- Apache httpd modules, `httpd-c-coding-practices`.
- Non-GNU embedded C with local `AGENTS.md` override.

## Workflow

1. **Format**, 79 cols, defun braces, GNU indent (`gnu-style-formatting-layout.md`).
2. **Naming**, identifiers, flags, files (`gnu-style-naming-files.md`).
3. **Comments**, English, `#endif` sense (`gnu-style-comments-conditionals.md`).
4. **Constructs/portability**, types, braces, Gnulib, errors (`gnu-style-constructs-portability.md`).
5. **Verify**, `./configure && make && make check`; optional GNU `indent` on touched C.

## Red Flags

- Function `{` not in column 1
- Lines >79 without intentional wrap
- `foo(bar)`, missing space before `(`
- CamelCase identifiers (`iCantReadThis`)
- CLI flag variable named only for letter, not meaning
- Missing function or static-variable comments
- `#endif` without condition/sense comment (nested blocks)
- Two spaces after period missing in new comment blocks
- `extern` inside function
- Nested `if`/`else` without braces
- Assignment inside `if` condition
- Unchecked `malloc`/`realloc`/syscall
- Error message without `strerror` + context
- Hand-rolled declaration of system function
- Kernel/httpd indent rules applied to GNU tree without project say-so

## Verification

- GNU `indent` with standards flags on changed files (optional separate commit)
- `grep -E '.{80}'` on touched lines
- `./configure && make check` (or project test target)
- Capsule probes on new conditionals and error paths
- Cross-check: not mixing httpd 4-space or kernel tab style


## References

- `awesome-guidelines/references/gnu-style-learning-note.md`
- `awesome-guidelines/references/gnu-style-formatting-layout.md`
- `awesome-guidelines/references/gnu-style-naming-files.md`
- `awesome-guidelines/references/gnu-style-comments-conditionals.md`
- `awesome-guidelines/references/gnu-style-constructs-portability.md`

## Related skills

- `c-coding-practices`, portable C safety baseline
- `httpd-c-coding-practices`, ASF httpd layout profile
- `shell-scripting-practices`, Autotools-adjacent shell glue
