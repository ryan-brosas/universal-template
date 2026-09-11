<!-- capsule-v2 -->
# Naming and constructs — are identifiers readable and forms idiomatic?

**Source:** Racket style §Names; §Choosing the Right Construct. **Question:** Do names signal type/role and control flow match data shape?

## Naming seam
**Path/Symbol:** functions, structs, classes in `.rkt` modules.
**Signature:** kebab-case English; `?` predicates; type-prefix selectors; `define`/`cond`/`for`.
**Data Shape:** `board-free-spaces`, `string-append`, `empty?`.

### Decisive pattern
```racket
(define (sum-up s)
  (for/fold ([total 0]) ([x s])
    (+ total x)))

(define (rate-item item rest)
  (cond
    [(discounted? item) (rate item)]
    [else (curved (g rest))]))

(define (process f)
  (define (complex-step x)
    ...))
  (map complex-step (sequence->list f)))
```

**Flow:** use full English words separated by dashes — no camelCase or underscores in regular names → prefix functions with main-argument type when helpful (`board-serialize`) → suffix predicates with `?`, mutators with `!`, classes with `%` → prefer internal `define` over nested `let` when it reduces indent → use `cond`, `case`, or `match` over nested `if`; `match` to destructure → prefer `for/list`, `for/fold`, etc. over `foldr`+long `lambda` → name multi-line helpers with `define`; reserve short `lambda` for `map`/`filter`/HOF slots → use structs for fixed small product types; functions over macros when possible.
**Invariant:** camelCase identifiers, underscore names, macro replacing expressible function, or nested `if`/`let` tower fails construct review.
**Probe:** naming convention audit; macro-vs-function grep on new exports.

## Traversal seam
**Flow:** decouple traversal from list-only APIs with `for/*`; use `values` as identity, not custom pass-through.
**Invariant:** list-only fold where sequence `for/fold` clarifies intent fails idiomatic review.
**Probe:** loop form spot check.

## Verdict
Kebab-case typed names, define/cond/for idioms, functions before macros. Learning note: `racket-style-learning-note.md`.
