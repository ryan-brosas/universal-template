<!-- capsule-v2 -->
# Formatting and layout — does Emacs Lisp indent and file shape match community norms?

**Source:** bbatsov Emacs Lisp style guide; GNU tips.texi. **Question:** Will `emacs-lisp-mode` indent and reviewers accept this layout?

## Indent seam
**Path/Symbol:** `.el` library files under package tree.
**Signature:** spaces only; `lexical-binding: t` first line; ≤80 columns.
**Data Shape:** blank lines between top-level forms; no hanging close-parens.

### Decisive pattern
```emacs-lisp
;;; projectile.el --- Project interaction library -*- lexical-binding: t; -*-

(defvar projectile--cache nil
  "Internal cache for project roots.")

(defun projectile-project-root ()
  "Return the root directory of the current project."
  (or projectile--cache
      (setq projectile--cache (projectile--find-root))))

(provide 'projectile)
;;; projectile.el ends here
```

**Flow:** line 1 file local `lexical-binding: t` → `indent-tabs-mode nil` (project `.dir-locals.el`) → Emacs indent for special forms (`when` body +2, special args +4) → align regular function args vertically → keep closing parens on the same line as the last form → blank line between top-level defs (group related `defconst`s together).
**Invariant:** hard tabs, missing lexical-binding on new code, or close-paren on its own line fails review.
**Probe:** `indent-tabs-mode` in `.dir-locals.el`; visual review; GNU tips “don't put close-parentheses on lines by themselves.”

## Spacing seam
```emacs-lisp
(when something
  (something-else))

(foo (bar baz) quux)   ; good — space around non-adjacent parens
```

**Flow:** space between text and non-adjacent `(` `)` → no space inside empty-pair adjacency → avoid lines >80 chars when feasible → no trailing whitespace.
**Invariant:** `(foo(bar baz)quux)` or internal `( bar )` padding fails review.
**Probe:** `checkdoc` / whitespace scan; line-length spot check.

## Verdict
Lexical-binding header, space indent, Emacs special-form rules, same-line close-parens. Learning note: `emacs-lisp-style-learning-note.md`.
