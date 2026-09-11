<!-- capsule-v2 -->
# Testing and verification — are regressions caught and exceptions precise?

**Source:** Racket style §Testing; §Exceptions/Parameters. **Question:** Does every bugfix add a rackunit case and do handlers name exact failure types?

## Test seam
**Path/Symbol:** `(module+ test …)` blocks and CI commands.
**Signature:** rackunit checks; test-first debug; `raco test`.
**Data Shape:** failing test → fix → re-run suite.

### Decisive pattern
```racket
(module+ test
  (require rackunit)
  (check-equal? (sum-up '(1 2 3)) 6))

(define (convert in f out)
  (with-handlers ([exn:fail:read? (lambda (e) (handle-read e))])
    (with-output-to out (writer f))))

(define (send-message msg op)
  (parameterize ([cop op])
    (display msg)
    (record msg)))
```

**Flow:** add rackunit tests in `(module+ test …)` at module end → run `raco test file.rkt` in CI → when fixing bugs, write failing test first, then patch, then rerun suite → use precise `with-handlers` predicates (`exn:fail:read?`) — never `(lambda (_ #t) #t)` or bare `exn?` (catches breaks) → use `exn:fail?` only when truly catching all failures, with handler that doesn't swallow unknown errors → use `parameterize` for dynamic settings instead of manual save/restore → split collections into singular module path names (`racket/contract` not `contracts`).
**Invariant:** handler that matches all exceptions, missing tests for reproduced bug, or manual parameter restore fails verify review.
**Probe:** `raco test` output; handler predicate audit; test submodule presence on changed modules.

## Verify seam
**Flow:** DrRacket "indent all" + tests green before merge; note at file top if tests depend on special indentation (rare).
**Invariant:** behavior-changing refactor without test update fails gate.
**Probe:** CI test job + indent-all check on touched files.

## Verdict
rackunit at module bottom, precise handlers, parameterize, raco test in CI. Learning note: `racket-style-learning-note.md`.
