---
title: common-lisp-coding-practices
summary: Use when authoring or reviewing Common Lisp, lisp-case naming, *earmuffs*/+constants+, SLIME indentation,:import-from packages, CLOS typed slots, defgeneric protocols, and ASDF test in CI.
kind: playbook
---

# Common Lisp Coding Practices

Application skill for Common Lisp style. For Emacs Lisp, use `emacs-lisp-coding-practices`.

## Core Principle

Common Lisp quality is **idiomatic names + explicit packages + documented CLOS**, small libraries, exported APIs only, SLIME-consistent layout.

## When to Use / NOT

- Common Lisp libraries, ASDF systems, SBCL/CCL deployments.
- Setting up SLIME indent, SBCL warnings, ASDF test-op in CI.

**NOT when:**

- Clojure/Scheme/Racket, use language-specific practice skills.
- Generated system stubs only, validate generator.

## Workflow

1. **Format & files**, indent, columns, headers.
2. **Naming**, lisp-case, *, +, predicates.
3. **Packages**, defpackage, ASDF.
4. **CLOS & control**, classes, when/unless.
5. **Verify**, load/test system; SBCL `(declaim (optimize ...))` policy; review exports.

## Red Flags

- camelCase or snake_case symbols
- `:use` heavy packages (beyond `:cl`)
- `other-package::internal` in production
- Missing docstrings on exported API
- `slot-value` in application logic
- Unrelated generic function overloads
- Commented-out code blocks
- Monolithic system with no library boundaries
- Abbreviated symbol names

## Verification

- `asdf:test-system` / project test script
- SBCL compile with project warning policy
- SLIME/common-lisp-indent style check
