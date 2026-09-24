# Account for shared spend across a mixed-model batch

Use when a paid batch spans several models, retries, or attempts launched at
different times and you intend to claim a spending limit. A per-model or
per-attempt guard is not a batch guarantee.

## Enforce at the effect boundary

A budget module that passes its own tests proves arithmetic, not enforcement.
Trace every path that can issue a provider request - main, executor, auxiliary
and retry calls - and confirm each one passes through the authority before the
request leaves. Until that wiring is exercised end to end, describe the limit as
a target, not a cap.

State which claim the evidence supports:

- **monitored spend** - recorded after the fact, with no admission control;
- **checked admission** - a request is refused when the projection would exceed
  the limit, but the authority is not the provider;
- **provider-enforced cap** - the provider itself refuses work.

Only the last supports an unqualified billing guarantee. Say which one is in
force, and keep receipts that record the residual uncertainty rather than
presenting the target as enforced.

## Reserve before, settle after

Reserve each request's worst-case cost from the model's own published rates
before dispatch, and settle with actual usage afterwards. One append-only ledger
that carries prior attempts forward lets an interrupted batch resume without
double-counting or silently resetting the balance; refuse to reopen an existing
journal as a fresh budget.

Treat usage as unknown, never as zero, when a request was aborted, timed out or
returned no finalized usage. Hold its reservation, mark the batch uncertain, and
let that uncertainty block further launches until it is resolved. If the usage
can never be finalized, close the batch with that hold reported as unresolved
exposure - never as zero and never as billed spend - and keep the batch marked
uncertain in its record. Predicted
exposure, recorded usage and billed cost are three different numbers; keep the
rates and their provenance beside every estimate.

## Sequence concurrent and mixed-model work

Sum every model's reservation against one batch total rather than giving each
model its own allowance. The admission check must be atomic: two simultaneous
reservations must not each see the same free remainder, so verify by attempting a
second reservation that should be refused. Retries and helper calls need their
own reservations; a retry is not free because the first attempt failed.

Report per-model amounts and unresolved holds separately, so a reader can
recompute the projection instead of trusting one aggregate.

## Boundaries

A conservative reservation deliberately overstates exposure: it is not evidence
of a defect and not actual spend. Do not convert estimates into billed costs, and
keep provider rate changes in the model-rate source rather than in prose.
