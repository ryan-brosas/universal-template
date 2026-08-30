<!-- capsule-v2 -->
# Formatting and files — is layout Emacs-consistent and files well-headed?

**Source:** lisp-lang style guide §Formatting; Google Lisp §Indentation, §File Header. **Question:** Will SLIME indentation and file headers match community norms?

## Layout seam
**Path/Symbol:** `.lisp` source files in Common Lisp projects.
**Signature:** 2-space body indent; ≤100 columns; blank line between top-level forms.
**Data Shape:** `;;;;` file comment; `(in-package ...)` early.

### Decisive pattern
```lisp
;;;; HTTP request parsing for the spider downloader.

(in-package :spider.http.request)

(defun parse-request-line
    (line)
  (let ((parts (split-sequence #\Space line)))
    (list :method (first parts)
          :path (second parts)
          :version (third parts))))
```

**Flow:** SLIME/cl-indent consistent style → 2 spaces per form level → wrap before 100 columns → one blank line between `defun`/`defclass` → gather long arg lists one per line.
**Invariant:** inconsistent manual indent, >100-column lines without team waiver, or missing `in-package` fails review.
**Probe:** Emacs `indent-region` / project slime style; line-length check in CI or review.

## File header seam
**Flow:** `;;;;` describes file purpose → no copyright/authorship in every file (use system README/LICENSE) → optional `declaim (optimize ...)` after package form per project policy.
**Invariant:** license boilerplate duplicated in every `.lisp` file fails review when ASDF/README already cover it.
**Probe:** first forms in file match header + `in-package` pattern.

## Verdict
SLIME indent, 100 cols, ;;;; header, in-package first. Learning note: `lisp-style-learning-note.md`.
