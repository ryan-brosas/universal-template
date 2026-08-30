<!-- capsule-v2 -->
# Packages and docs — are load boundaries, autoloads, and docstrings correct?

**Source:** bbatsov Loading/Docstrings; GNU Library Headers & Documentation Tips. **Question:** Can users require this feature safely and read docs in Emacs help?

## Package seam
**Path/Symbol:** library `.el` headers, requires, footers.
**Signature:** `(require 'dep)`; `(provide 'feature)`; selective autoload cookies.
**Data Shape:** standard `;;; foo.el ---` header block.

### Decisive pattern
```emacs-lisp
;;; foo.el --- Frobnicate buffers -*- lexical-binding: t; -*-

;; Author: Ada Lovelace <ada@example.com>
;; Keywords: convenience

(require 'cl-lib)

(eval-when-compile (require 'bar-macro-lib))

;;;###autoload
(defun foo-setup ()
  "Enable Foo mode in the current buffer."
  (interactive)
  (foo-mode 1))

(provide 'foo)
;;; foo.el ends here
```

**Flow:** standard header with summary + lexical-binding → document deps in header → `require` (not `load`) at top when always needed, else lazy inside functions → macro-only deps via `eval-when-compile` → autoload cookies on modes/setup commands only, not internals → end with `provide` + ends-here comment → use `cl-lib` not deprecated `cl`.
**Invariant:** autoload on `foo--internal`, top-level side-effect autoload, or missing `provide` fails MELPA review.
**Probe:** `package-lint`; grep `;;;###autoload` targets; `require` vs `load-library` audit.

## Docstring seam
```emacs-lisp
(defun foo-goto-line (line &optional buffer)
  "Go to LINE in BUFFER, counting from 1 at beginning of buffer.
If BUFFER is nil, use the current buffer."
  ...)
```

**Flow:** every user-facing symbol gets docstring → first line complete imperative sentence → describe args in UPCASE in call order → do not indent continuation lines in source → capitalize “Emacs” → run `checkdoc` / Flycheck.
**Invariant:** indented docstring continuations or missing docs on public commands fails review.
**Probe:** `M-x checkdoc-current-buffer`; `checkdoc-file` in CI batch.

## Verdict
Header + require/provide/autoload discipline and checkdoc-clean docstrings. Learning note: `emacs-lisp-style-learning-note.md`.
