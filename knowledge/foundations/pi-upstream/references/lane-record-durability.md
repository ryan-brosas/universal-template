<!-- capsule-v2 -->
# Lane-record durability — how does a session survive crashes mid-operation and know what it was doing?

**Source:** pi-upstream MIT `main@534bcbffb7e1e7551d9ee3572dfeb278e203e493`; Codebase Memory `pi-upstream`. **Question:** A porter persists only conversation entries — what must ALSO be persisted for recovery, and how is corruption detected?

## Entries are history; records are the operation log; lanes own leaf pointers
**Path/Symbol:** `packages/agent/src/harness/session/types.ts:80-215` (LaneRecord union), `:290-326` (`SessionStorage` incl. `findOpenOperations`), `:273-276` (`LanePointer`).
**Signature:** `findOpenOperations(lane, options?): Promise<OperationStartedRecord[]>` with the documented recovery contract; every record carries `{id, seq, lane, timestamp}`.
**Data Shape:** Record types: `operation_started` (intent = run | compaction | navigation, carrying originalPrompt / initialMessages / resultEntryId / summaryEntryId), `abort_requested`, `operation_finished` (completed/aborted/failed/declined + error), `step_attempt` (assistant | branch_summary | compaction + attempt + compactionReason so recovery resumes the SAME work), `tool_started` (effectiveArgs + replay: "never"|"safe"), `queue_enqueued` (steer | followUp | nextRun), `queue_cancelled`, `write_deferred`, `usage`.

### Decisive source
```ts
/**
 * Returns unfinished operation starts newest first. Recovery uses `limit: 2`:
 * zero results mean the lane is idle, one means it is suspended, and two
 * mean at least two operations are open, which is corruption. Further
 * results provide no additional recovery state.
 */
findOpenOperations(lane: string, options?: { limit?: number }): Promise<OperationStartedRecord[]>;
```
And on step_attempt: `"Persists why compaction summary generation started so recovery resumes the same work."`

**Flow:** every operation writes its intent FIRST (durable-create-before-act) → progress records (step attempts, tool starts, queue enqueues) accumulate under the same runId → terminal `operation_finished` closes it. On restart, a lane reads its open operations: 0 = idle, 1 = resume from recorded intent/attempts, ≥2 = refuse as corruption. Entries attach to a LANE's leaf (`parentId` = "the appending lane's leaf"), so concurrent lanes branch independently in one store.
**Invariant:** Intent-before-effect ordering plus the 0/1/2+ open-operation tri-state makes crash recovery decidable without heuristics; tool_started records carry replay-safety classification ("never" vs "safe") so recovery never re-runs an unsafe side effect blindly.
**Probe:** No dedicated unit suite for findOpenOperations at this HEAD — coverage caveat; deterministic probes: type-level contract at `packages/agent/src/harness/session/types.ts:311-317`, storage conformance harness at `packages/agent/src/harness/session/testing/conformance.ts`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-upstream", query: "findOpenOperations OperationStartedRecord lane", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt intent-first operation records + tri-state recovery + replay classification. Adapt record vocabulary to your operation set. Omit queue/write-deferred records if your host has no cross-run queues. Coverage caveat: recovery ladder itself untested upstream at this HEAD — treat the doc comment as the contract.
