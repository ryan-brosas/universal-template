<!-- capsule-v2 -->
# Textual layout — does DrRacket indent-all leave the file unchanged?

**Source:** Racket style §Textual Matters. **Question:** Are parens, width, and comments shaped for diff-friendly reading?

## Layout seam
**Path/Symbol:** `.rkt` modules and `#lang` files.
**Signature:** DrRacket indentation; closers on last line; ≤102 columns; no tabs.
**Data Shape:** `;;` section rulers; `;` vs `;;` comments.

### Decisive pattern
```racket
#lang racket

;; -------------------------------------------------------------------
;; board serialization

(define (board-serialize board)
  (cond
    [(empty-board? board) '()]
    [else
     (define free (board-free-spaces board))
     (list 'board free (board-closed-spaces board))]))

(define MODES
  '(edit help debug test trace step))
```

**Flow:** use DrRacket indentation — repo files should survive "indent all" unchanged → put closing parens on the last line of the form (not C-style dangling `)` mid-file) → max 102 characters per line; add `;;` ruler lines between sections → no tab characters; trim trailing whitespace → end file with newline → break multiline `if` with each alternative on its own line → one definition per line minimum → break long call args one per line when needed → use `;` for end-of-line comments, `;;` for full-line comments, `#;` to toggle expressions.
**Invariant:** tabs, >102-char unbroken lines, or DrRacket re-indent diff fails textual review.
**Probe:** DrRacket "Indent All"; width ruler; `grep $'\t'`.

## Paren/spacing seam
**Flow:** space between adjacent expressions on a line; no graphical syntax boxes in source.
**Invariant:** comment-box/XML-box sources or cramped `(f(x))` without spacing fail portability review.
**Probe:** visual spacing check; no graphical-syntax grep.

## Verdict
DrRacket-shaped indent, last-line closers, 102-col discipline, semicolon comment tiers. Learning note: `racket-style-learning-note.md`.
