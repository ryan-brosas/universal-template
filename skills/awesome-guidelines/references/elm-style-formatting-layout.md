<!-- capsule-v2 -->
# Formatting and layout — is elm-format applied and declaration shape regular?

**Source:** Elm official style guide; NoRedInk guide. **Question:** Do top-level declarations follow predictable layout for clean diffs?

## Format seam
**Path/Symbol:** `.elm` modules under `src/`.
**Signature:** `elm-format`; ≤80 columns; body on next line.
**Data Shape:** two blank lines between top-level declarations.

### Decisive pattern
```elm
module Post exposing (Post, decoder, encode, wordCount)


homeDirectory : String
homeDirectory =
    "/root/files"


evaluate : Boolean -> Bool
evaluate boolean =
    case boolean of
        Literal bool ->
            bool

        Not b ->
            not (evaluate b)

        And b b_ ->
            evaluate b && evaluate b_
```

**Flow:** run `elm-format` on every change → keep lines ≤80 when feasible → type annotation on every top-level definition → `=` then body on next line → two empty lines between top-level defs.
**Invariant:** missing type annotation, inline `case` on function head line, or unformatted diff fails review.
**Probe:** `elm-format --validate`; line-length review.

## Readability seam
**Flow:** prefer regularity over vertical compression → when a `case` branch grows, surrounding structure should not require mass re-indent of unrelated lines.
**Invariant:** cramming entire `case` on one line after `=` fails review.
**Probe:** diff size review when adding a union constructor.

## Verdict
elm-format, annotated top-level defs, body on next line, double spacing. Learning note: `elm-style-learning-note.md`.
