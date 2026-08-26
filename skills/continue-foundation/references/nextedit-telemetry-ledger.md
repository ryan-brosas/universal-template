<!-- capsule-v2 -->
# NextEdit outcome telemetry ledger — displayed-then-10s-rejected default, prefix-continuation cancellation, abort-only-if-displayed

**Source:** Continue (Apache-2.0) `main@5522c6f44ca0ac3528b37244818fbfa39b5af470`; Codebase Memory `continue`. **Question:** How does the next-edit pipeline decide an outcome was accepted vs rejected vs aborted, given only implicit user signals?

## Key facts
**Path/Symbol:** `core/nextEdit/NextEditLoggingService.ts` (whole, 219L) — `markDisplayed` (:136-180), `accept`/`reject` (:84-117), `handleAbort` (:182-202), `cancelRejectionTimeout` (:119-128), pending-completion tracking (:36-74).
**Signature:** `markDisplayed(completionId, outcome)` arms a `setTimeout(COUNT_COMPLETION_REJECTED_AFTER)` rejection timer; `accept(id)` / `reject(id)` clear it and log immediately; singleton via `getInstance()`.
**Data Shape:** four maps keyed by completionId: `_abortControllers`, `_logRejectionTimeouts`, `_outcomes`, `_pendingCompletions` (minimal `{startTime, modelName?, modelProvider?, filepath?}` for requests that die before producing a full outcome); plus `_lastDisplayedCompletion: {id, displayedAt}`.

### Decisive source
```ts
// :141-148 — DEFAULT IS REJECTION after the timeout:
const logRejectionTimeout = setTimeout(() => {
  // Wait 10 seconds, then assume it wasn't accepted
  outcome.accepted = false; outcome.aborted = false;
  this.logNextEditOutcome(outcome);
  ...
}, COUNT_COMPLETION_REJECTED_AFTER);

// :156-173 — don't count a REPLACED suggestion as a rejection:
if (previousOutcome &&
    (c1.endsWith(c2) || c2.endsWith(c1) || c1.startsWith(c2) || c2.startsWith(c1)))
  this.cancelRejectionTimeout(previous.id);        // continuation of same edit
else if (now - previous.displayedAt < 500)
  this.cancelRejectionTimeout(previous.id);        // flashed < 500ms — not a real rejection

// :189-196 — aborts only count for outcomes that REACHED THE SCREEN:
// "Only log if the completion was displayed to the user."
if (this._outcomes.has(completionId)) { outcome.aborted = true; this.logNextEditOutcome(outcome); }
```

**Flow:** request registers a pending completion at init (abort controller creation or external-token tracking), enriched with model info once resolved → on display, the full outcome is stored and the rejection timer armed; accept/reject flip the flag, clear timer + maps, and log exactly once; cancel() aborts every live controller (each abort logs ONLY if displayed). First-line prefix/suffix comparisons (`split("\n")[0]`) decide whether the new suggestion continues the old one.

**Invariant:** telemetry is single-shot per completionId — every terminal path deletes the id from `_outcomes` before/while logging, so double-accept or accept-after-timeout is structurally impossible to double-count. The 500ms flash window and first-line continuation test are BOTH needed: without them, normal retyping inflates rejections and deflated accepts corrupt model-choice decisions downstream.

**Probe:** `grep -c 'COUNT_COMPLETION_REJECTED_AFTER' core/nextEdit/NextEditLoggingService.ts` → 2 (:1 import, :148 timer); `grep -c 'c1.endsWith(c2)' core/nextEdit/NextEditLoggingService.ts` → 1; `grep -c 'now - previous.displayedAt < 500' core/nextEdit/NextEditLoggingService.ts` → 1; `grep -c 'this._outcomes.delete(completionId)' core/nextEdit/NextEditLoggingService.ts` → 5.

**Retrieve:** `await mcp.codebase_memory.search_graph({ project: "continue", query: "NextEditLoggingService markDisplayed rejection timeout handleAbort", limit: 8 })`

## Verdict
Adopt displayed→timeout-rejects as the default branch with explicit continuation (<500ms or first-line prefix match) and abort-only-if-displayed exceptions; enforce single-shot logging by map deletion at every exit.
