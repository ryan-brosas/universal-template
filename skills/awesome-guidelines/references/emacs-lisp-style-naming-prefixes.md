<!-- capsule-v2 -->
# Naming and prefixes — are globals namespaced and predicates idiomatic?

**Source:** bbatsov guide; GNU Coding Conventions (tips.texi). **Question:** Will this symbol collide in the shared Emacs namespace?

## Prefix seam
**Path/Symbol:** global `defun` / `defvar` / `defcustom` in libraries.
**Signature:** `library-prefix-name`; `--` private; `-p` predicates.
**Data Shape:** `lisp-case` identifiers.

### Decisive pattern
```emacs-lisp
(defconst projectile-max-file-count 100000)

(defun projectile-project-root ()
  "Return the root directory of the current project."
  ...)

(defun projectile--find-root ()
  "Internal helper; not part of public API."
  ...)

(defun projectile-live-p ()
  "Return non-nil when inside a recognized project."
  ...)
```

**Flow:** pick short library prefix → prefix every global variable/function → use `--` for internal top-level defs → predicate ends in `p` (one word) or `-p` (multi-word) → use `lisp-case` not camelCase or snake_case → unused lexical locals prefixed with `_`.
**Invariant:** unprefixed `(defun project-root ...)`, `palindrome?`, or `widget-inactive-face` fails review.
**Probe:** grep `^(defun\|defvar\|defcustom)` for missing prefix; predicate name audit.

## GNU namespace seam
**Flow:** loading must not change editing behavior — expose explicit enable/disable commands → for file names use `file-name`/`directory`, reserve `path` for search-path lists → do not bind `C-c letter` in packages (user-reserved).
**Invariant:** side effects at load time or user-key theft fails MELPA/GNU review.
**Probe:** load file in clean Emacs — no hooks/modes altered until enable command; keymap audit for `C-c` + letter.

## Verdict
Prefixed lisp-case globals, `--` private, `-p` predicates, load-safe namespace. Learning note: `emacs-lisp-style-learning-note.md`.
