---
title: emacs-lisp-coding-practices
summary: Use when authoring or reviewing Emacs Lisp, lexical-binding, lisp-case prefixes, when/unless idioms, sharp quotes, provide/require/autoload, docstrings, and checkdoc/package-lint/byte-compile in CI.
kind: playbook
---

# Emacs Lisp Coding Practices

Application skill for Emacs Lisp style. For major/minor mode APIs and key-binding policy details, consult the framework's own source or docs.

## Core Principle

Emacs Lisp quality is **namespace-safe, load-safe regularity**, lexical scoping, prefixed globals, Emacs indent, and docstrings that survive `checkdoc`.

## When to Use / NOT

- Emacs packages, `.el` libraries, init snippets intended for distribution.
- Setting up `checkdoc`, `package-lint`, byte-compile warnings in CI.

**NOT when:**

- One-off `M-x eval` experiments not committed to a library.
- Non-Emacs Lisp code.

## Workflow

1. **Layout**, lexical-binding, indent, parens.
2. **Names**, prefixes, private `--`, predicates.
3. **Functions**, when/unless, quotes, macros.
4. **Packages**, header, require/provide/autoload, docs.
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
