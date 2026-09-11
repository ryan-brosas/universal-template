<!-- capsule-v2 -->
# Formatting and layout — is indentation and line length review-friendly?

**Source:** HaskellWiki Programming guidelines; Tibbe style guide. **Question:** Do diffs show semantics without layout noise?

## Layout seam
**Path/Symbol:** `*.hs` / `*.lhs` modules.
**Signature:** 4-space indent; ≤80 columns; final newline.
**Data Shape:** case alternatives aligned after `of`.

### Decisive pattern
```haskell
filter :: (a -> Bool) -> [a] -> [a]
filter _ [] = []
filter p (x : xs)
    | p x       = x : filter p xs
    | otherwise = filter p xs

parseStatus :: Text -> Either ParseError Status
parseStatus raw =
    case Text.strip raw of
        "ok" -> Right Ok
        "fail" -> Right Fail
        other -> Left (UnexpectedToken other)
```

**Flow:** spaces not tabs → 4-space block indent → `where` keyword indented +2, its defs +2 more → max ~80 columns; refactor long expressions → one blank line between top-level defs; none between type sig and definition → break `case … of` before alternatives (no `{ ; }` brace style) → `\ t ->` space after lambda → file ends with newline; no trailing whitespace.
**Invariant:** tabs, >80-char default lines, brace-case layout, or sig/definition blank line gap fails review.
**Probe:** stylish-haskell/fourmolu diff; `scan` or editor trailing-ws check.

## Module size seam
**Flow:** keep modules ~400 lines guideline — split when cohesion breaks.
**Invariant:** monolithic 2000-line module without domain seam fails maintainability review.
**Probe:** line count per module.

## Verdict
4-space layout, 80 cols, aligned case, tidy blank lines. Learning note: `haskell-style-learning-note.md`.
