---
name: emacs-lisp-coding-practices
description: "Use when authoring or reviewing Emacs Lisp, lexical-binding, lisp-case prefixes, when/unless idioms, sharp quotes, provide/require/autoload, docstrings, and checkdoc/package-lint/byte-compile in CI."
disable-model-invocation: true
---

# Emacs Lisp Coding Practices

Application skill for Emacs Lisp style learning (from the archived `awesome-guidelines` style capsules). For major/minor mode APIs and key-binding policy details, combine with stack-specific foundations.

## Core Principle

Emacs Lisp quality is **namespace-safe, load-safe regularity**, lexical scoping, prefixed globals, Emacs indent, and docstrings that survive `checkdoc`.

## When to Use / NOT

- Emacs packages, `.el` libraries, init snippets intended for distribution.
- Setting up `checkdoc`, `package-lint`, byte-compile warnings in CI.

**NOT when:**

- One-off `M-x eval` experiments not committed to a library.
- Non-Emacs Lisp code.

## Workflow

1. **Layout**, lexical-binding, indent, parens (`emacs-lisp-style-formatting-layout.md`).
2. **Names**, prefixes, private `--`, predicates (`emacs-lisp-style-naming-prefixes.md`).
3. **Functions**, when/unless, quotes, macros (`emacs-lisp-style-functions-macros.md`).
4. **Packages**, header, require/provide/autoload, docs (`emacs-lisp-style-packages-docs.md`).
5. **Verify**, `checkdoc-file`, `package-lint`, `byte-compile-file` on changed `.el` files.

## Red Flags

- Missing `lexical-binding: t` on new files
- Hard tabs or hanging close-parens
- Unprefixed global symbols
- Side effects when library loads
- Hard-quoted lambdas in hooks/keys
- `(if ... (progn ...))` for multi-form branches
- Autoload on internal helpers
- `load-library` instead of `require`
- Deprecated `cl` instead of `cl-lib`
- Docstrings with indented continuation lines
- `C-c letter` bindings in packages
- Macros where plain functions work

## Verification

- `emacs -batch -l checkdoc.el -f checkdoc-file -- FILE.el`
- `package-lint` (MELPA-bound packages)
- `byte-compile-file` with warnings treated as errors (project policy)
- Capsule checklist on public `defun` docstrings


## References

- `awesome-guidelines/references/emacs-lisp-style-learning-note.md`
- `awesome-guidelines/references/emacs-lisp-style-formatting-layout.md`
- `awesome-guidelines/references/emacs-lisp-style-naming-prefixes.md`
- `awesome-guidelines/references/emacs-lisp-style-functions-macros.md`
- `awesome-guidelines/references/emacs-lisp-style-packages-docs.md`
