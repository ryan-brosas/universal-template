<!-- capsule-v2 -->
# Lease-gated interval runners — how do multiple app instances share one analyzer loop without a scheduler service?

**Source:** teable AGPL `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** How does the background analyzer/task-worker coordinate across processes using only an optional lease repository?

## Acquire-then-skip with TTL = interval, and undefined-means-run
**Path/Symbol:** `packages/v2/table-query-ops/src/runners.ts`: `startTableQueryOpsAnalyzerIfEnabled` (:26-37), `runAnalyzerOnce` (:54-93), `runTaskWorkerOnce` (:95-132), `resolveOptionalLogger/LeaseRepository` (:134-144).
**Signature:** `leaseRepository?.acquire(context, {leaseKey:'table-query-ops-analyzer', ownerId: config.workerId, ttlMs: config.intervalMs, now})` → `Result<boolean>`; run proceeds only on `ok(true)`.
**Data Shape:** analyzer reads `observationReader.findRecent({since: now - lookbackMs, limit: batchSize})` then executes one AnalyzeAndRecommend command per window; task worker claims one accepted task per tick (`claimNextAccepted`) and runs it via the bus. Both loops: immediate first run + `setInterval`, `{stop}` handle.

### Decisive source
```ts
const acquired = await leaseRepository?.acquire(context, { leaseKey, ownerId, ttlMs: config.intervalMs, now });
if (acquired && (acquired.isErr() || acquired.value === false)) return;  // Err or lost lease ⇒ SKIP this tick
```

**Flow:** tick → (optional) lease acquire → read recent observation windows → for each, dispatch AnalyzeAndRecommend through the REAL command bus (so handlers' own DI, logging, tracing apply) → per-item errors logged and CONTINUED (one bad window never kills the batch).
**Invariant:** The lease TTL equals the interval so leases expire exactly when the next tick fires — no renewal machinery needed. `undefined` lease repo (feature off) means EVERY instance runs — acceptable because analysis is idempotent upserts, not execution; the TASK worker instead relies on the DB-level claim (SKIP LOCKED) which is safe uncoordinated. Fail-open on lease ERROR mirrors the foundation's distributed-lock posture.
**Probe:** no direct spec at this HEAD — contract pinned by ports interface + di.spec wiring. Coverage caveat recorded.
**Coverage caveat:** runner internals lack direct tests upstream; behavior verified against source + port contracts only.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "runAnalyzerOnce TableQueryOpsLeaseRepository acquire claimNextAccepted", limit: 6, fields: ["signature","name","file"] });
```

## Verdict
Adopt TTL-equals-interval leasing and continue-on-per-item-error batching; adapt intervals; note the deliberate asymmetry (lease-coordinated analyzer vs DB-claimed worker) — copying either half onto the wrong loop is the porting mistake.
