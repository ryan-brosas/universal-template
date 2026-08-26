<!-- capsule-v2 -->
# Compact intent single slot — how does a model request context compaction without ever compacting mid-turn?

**Source:** pi-fabric (MIT), `feat/veda-runner@4874ac3a`; Codebase Memory `pi-fabric`. **Question:** How do you let an LLM ask for context compaction while guaranteeing only the HOST decides when it happens?

## Compact intent single slot
**Path/Symbol:** `src/core/compact-controller.ts:CompactController.request/maybeCommit/cancel/status` (:88–120, commit :125–218).
**Signature:** `request(intent: CompactRequestIntent): CompactPendingIntent`; `async maybeCommit(context: ExtensionContext): Promise<void>`.
**Data Shape:** Intent `{reason?, instructions?, preserve?: string[], requestedBy?}` → pending adds `requestedBy` (default `"model"`) + `requestedAt: Date.now()`; last-commit record `{at, requestedBy, status: "committed"|"cancelled"|"failed", summary?, tokensBefore?, estimatedTokensAfter?, error?}`.

### Decisive source
```ts
// This mirrors Schema's harness-enforced gate: there is exactly one write path
// from thought (intent) to action (commit), and the host — not the model —
// decides when it is safe.
request(intent: CompactRequestIntent): CompactPendingIntent {
    const boundsError = compactionRequestBoundsError(request);
    if (boundsError) throw new Error(boundsError.message);
    ...
    this.#pending = pending;   // SINGLE slot: new request replaces any pending one
```

**Flow:** model calls `request()` → intent lands in ONE replaceable slot → host's `agent_settled` handler awaits `maybeCommit(context)` → `context.compact({customInstructions, onComplete, onError})` settles via callback → `#last` records outcome, `#pending` cleared by identity check `this.#pending === committing`.
**Invariant:** The model can NEVER compact directly; `maybeCommit` is idempotent per boundary (`if (this.#inFlight) return this.#inFlight;` — a second call during flight neither double-compacts nor loses the newer pending intent, which survives for the NEXT boundary); errors matching exactly `"Compaction cancelled"` or `"Already compacted"` are recorded as status `"cancelled"` (NOT failed) yet still clear the pending intent; aborted-boundary or sync-throw paths settle through the same `finish()` latch (`callbackSettled`) so callbacks can never fire twice.
**Probe:** `tests/compact-controller.test.ts` ("keeps ExtensionRunner agent_settled pending until compaction completes" pins the public-event ordering: timeline is `["handler:start"]` until `onComplete`, then `handler:end`, then `public:agent_settled`); grep -c 'records ''Compaction cancelled'' as cancelled, not failed' tests/compact-controller.test.ts → 1.
**Anchor:** repo root.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-fabric", query: "CompactController maybeCommit pending intent compaction", limit: 10 });
// CompactController.maybeCommit Method src/core/compact-controller.ts 125-218
```

## Verdict
Adopt the single-slot intent + host-committed-at-settled-boundary pattern verbatim for any agent harness with LLM-initiated context management; adapt the Pi `context.compact()` callback shape to your host's API; omit the typed `preserve` encode step unless you port `compaction-typed-instructions` too.
