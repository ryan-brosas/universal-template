<!-- capsule-v2 -->
# Functions and macros — are control flow and quoting byte-compiler friendly?

**Source:** bbatsov guide §Syntax/Functions/Macros; GNU Programming Tips. **Question:** Will this compile cleanly and compose like ordinary functions?

## Control-flow seam
**Path/Symbol:** conditionals and iteration in `.el` bodies.
**Signature:** `when`/`unless`; `null` vs `not`; `t` in `cond`.
**Data Shape:** `#'` function quotes; plain functions over macros.

### Decisive pattern
```emacs-lisp
(when (and buffer (null (buffer-live-p buffer)))
  (error "Buffer is dead"))

(cond
 ((< n 0) "negative")
 ((> n 0) "positive")
 (t "zero"))

(cl-remove-if-not #'evenp numbers)

(dolist (hook '(prog-mode-hook text-mode-hook))
  (add-hook hook #'turn-on-column-number-mode))
```

**Flow:** multi-form conditionals → `when`/`unless` not `(if ... (progn ...))` → test empty lists with `null`, general negation with `not` → `cond` catch-all is `t` → prefer `1+`/`1-`, chained numeric compares → side-effect iteration → `dolist`/`seq-do` not discard `mapcar`.
**Invariant:** `(if pred (progn ...))`, `:else` in `cond`, or `(mapcar 'load files)` for effects fails review.
**Probe:** grep `(if .* (progn` and `:else`; byte-compile warnings.

## Quote & lambda seam
```emacs-lisp
(add-hook 'my-hook #'my-save-buffers)

;; bad — blocks byte-compilation
(add-hook 'my-hook '(lambda () (save-some-buffers)))
```

**Flow:** function symbols → `#'name` sharp quote → lambdas only for local/mapcar one-offs → named `defun` for hooks, keys, customs → never hard-quote lambda → macros only when functions cannot (compile-time transform); macro delegates to functions with `(declare (debug t))`.
**Invariant:** hard-quoted lambda, macro where function suffices, or >4 positional args without `cl-defun` keywords fails review.
**Probe:** grep `'(lambda` and `'[a-z]` in functional positions; arity review.

## Verdict
when/unless, sharp quotes, named hook functions, macros as last resort. Learning note: `emacs-lisp-style-learning-note.md`.
