<!-- capsule-v2 -->
# Modules and contracts — is the interface top-down and bounded?

**Source:** Racket style §Units of Code. **Question:** Can a reader see exports, contracts, and main services without scrolling past implementation?

## Module seam
**Path/Symbol:** `#lang racket` module files and packages.
**Signature:** purpose line; `(provide …)` with comments; `contract-out`; top-down defs.
**Data Shape:** provide section → require → implementation → `(module+ test …)`.

### Decisive pattern
```racket
#lang racket/base

;; TV server/client helpers

(require racket/contract)

(provide
  (contract-out
    [tv-launch (-> void?)]
    [tv-client (-> void?)]))

(require 2htdp/universe)

(define (tv-launch)
  (universe ...))

(define (tv-client)
  (big-bang ...))

(module+ test
  (require rackunit)
  (check-not-exn (tv-launch)))
```

**Flow:** start module with short purpose statement → place `(provide …)` near top with per-export purpose comments and `contract-out` when possible → group requires: contracts first if needed, implementation requires below provide → organize top-down: important public functions before helpers → keep modules ~500 lines when practical; functions ~screen height (~66 lines) → use explicit `(provide id …)` not `(all-defined-out)` → uniform parameter order/naming within module → separate sections with `;;` rulers or submodules → put `(module+ test …)` at end with test-only requires.
**Invariant:** scattered provide at file bottom, missing export docs, or multi-thousand-line module without split fails units review.
**Probe:** provide-at-top grep; line-count spot check; contract-out on public API.

## Contract seam
**Flow:** contracts at module boundary; `define/contract` or submodules for internal boundaries in large files.
**Invariant:** undocumented exported function on ADT module fails boundary review.
**Probe:** export list vs documented services checklist.

## Verdict
Documented provide/contract-out header, top-down layout, small units, test submodule last. Learning note: `racket-style-learning-note.md`.
