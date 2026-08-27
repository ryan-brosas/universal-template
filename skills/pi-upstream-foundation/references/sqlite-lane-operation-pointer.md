<!-- capsule-v2 -->
# Lane open-operation pointer — how do you enforce "at most one in-flight operation per lane" so the crash-recovery tri-state can't even represent corruption?

**Source:** pi-upstream MIT `main@4af9d21d3b4d`; Codebase Memory `pi-upstream`. **Question:** Where does single-open-operation admission live when storage is transactional, and what does the recovery read return when the JSONL backend would have found two competing starts?

## SQL CAS on a nullable pointer; recovery reads the pointer, not a scan
**Path/Symbol:** `packages/session-backends/sqlite-node/src/sqlite/storage/lanes.ts:startLaneOperation` (:88–95), `finishLaneOperation` (:97–100); `storage/records.ts:readOpenOperationRows` (:73–95); schema `lanes.open_operation_id` (`001_initial.sql:58-64`).
**Signature:** `startLaneOperation(db, sessionId, lane, runId)`; `readOpenOperationRows(db, sessionId, lane, options?): RecordRow[]`.
**Data Shape:** `appendRecord` calls `startLaneOperation` for `operation_started` and `finishLaneOperation` for `operation_finished` INSIDE the same lease-renewed transaction as the record insert (repo.ts:495-510).

### Decisive source
```ts
const result = sql`UPDATE lanes SET open_operation_id = ${runId}
	WHERE session_id = ${sessionId} AND lane = ${lane} AND open_operation_id IS NULL`.run(db);
if (result.changes === 1) return;
const current = readLane(db, sessionId, lane);
if (!current) throw new SessionError("invalid_lane", `Lane not found: ${lane}`);
throw new SessionError("storage", `Lane ${lane} already has an open operation ${current.open_operation_id}`);
```
and the recovery read:
```ts
if (!laneRow?.open_operation_id) return [];
const record = sql`SELECT … FROM records WHERE session_id = ${sessionId} AND id = ${laneRow.open_operation_id}`.get<RecordRow>(db);
if (!record) throw new SessionError("storage", `Lane ${lane} points at missing open operation ${laneRow.open_operation_id}`);
if (record.lane !== lane || record.type !== "operation_started") {
	throw new SessionError("storage", `Lane ${lane} points at invalid open operation ${laneRow.open_operation_id}`);
}
return [record];
```

**Flow:** start = conditional UPDATE claiming the NULL pointer (changes≠1 → named conflict error carrying the current holder's id); finish = clear only where the pointer still equals THIS runId (no-throw — superseded finishes vanish); `findOpenOperations` dereferences the pointer and returns [] or exactly [record], validating referential integrity (missing/mistyped target → storage error). The interface docstring's tri-state (0 idle / 1 suspended / 2+ corruption) collapses structurally: two open ops are unrepresentable in one nullable column.
**Invariant:** admission control is atomic with the record append (same transaction), and recovery state is O(1) derived data — never re-derived by scanning records for unmatched starts.
**Probe:** deterministic SQL probe P4 executed this pass (verification.md): second `startLaneOperation` on a claimed lane returns changes=0 → error path; `finishLaneOperation` with wrong runId leaves the pointer set. Upstream direct coverage rides the shared conformance suite (`conformance.ts` open-operation groups).

## The same contract, two derivations — scan index vs nullable pointer
**Path/Symbol:** contract docstring `packages/agent/src/harness/session/types.ts:findOpenOperations` (:311–317); scan side `state.ts:SessionState.applyMutation` record case (:126–141) + `SessionState.findOpenOperations` (:229–234), delegated by `memory.ts:112-114` and `jsonl/storage.ts:215-216`; pointer side `storage/records.ts:readOpenOperationRows` (:73–95).
**Signature:** both sides implement the same `findOpenOperations(lane, { limit? }): OperationStartedRecord[]`.

### Decisive source
```ts
// types.ts:311-317 — the tri-state is a READ-SIDE convention, not a storage guarantee
/**
 * Returns unfinished operation starts newest first. Recovery uses `limit: 2`:
 * zero results mean the lane is idle, one means it is suspended, and two
 * mean at least two operations are open, which is corruption. Further
 * results provide no additional recovery state.
 */
findOpenOperations(lane: string, options?: { limit?: number }): Promise<OperationStartedRecord[]>;
```
```ts
// state.ts:132-141 — scan side: index maintained from the persisted record stream
if (mutation.record.type === "operation_started") {
	…openOperations.set(mutation.record.id, mutation.record);
} else if (mutation.record.type === "operation_finished") {
	this.openOperationsByLane.get(mutation.record.lane)?.delete(mutation.record.runId);
}
// state.ts:229-234 — newest-first reversal + limit slice
const openOperations = openOperationsById ? [...openOperationsById.values()].reverse() : [];
return options?.limit === undefined ? openOperations : openOperations.slice(0, options.limit);
```

**Flow:** the 0/1/2+ tri-state lives in the CONTRACT's reading convention (recovery asks with `limit: 2`), not in any storage guarantee. The scan side derives its answer from the record stream: the per-lane id map CAN hold 2+ entries, so a replayed log with two unmatched starts yields `[a, b]` and the corruption arm is REACHABLE — detectable, and classified downstream as `multiple_open_operations`. The pointer side dereferences one nullable column and returns [] or [record] with referential validation: 2+ is unrepresentable, so the same arm is ELIMINATED rather than detected. Orphaned finishes are inert on both sides — index `delete(runId)` on a missing key is a no-op; the pointer's `UPDATE … WHERE open_operation_id = runId` matches zero rows (no-throw) — pinned cross-backend by conformance case "does not let an earlier finish close a later start" (:505–521). Write-time admission (memory.ts:75-79 / jsonl/storage.ts:175-181 throw; the CAS above throws) is what keeps both derivations honest.
**Invariant:** the tri-state must stay a read-side convention: a backend may make the corruption arm structurally impossible instead of merely detectable, but recovery code must still be written against the `limit: 2` shape because the scan backends genuinely reach it.
**Probe:** deterministic probes P1/P2 executed this pass (verification.md): a corrupted two-start replay returns both ids from the transcribed index (arm 3 reachable) while the second pointer CAS returns changes=0 (unrepresentable); orphaned-finish no-op verified on both mechanisms. Upstream direct coverage: conformance cases :483–503 ("tracks and enforces one open operation per lane" — runs exactly the `limit: 2` probe shape on every backend fixture) and :505–521.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-upstream", name_pattern: ".*(startLaneOperation|readOpenOperationRows)", limit: 10 });
```

## Verdict
Adopt: pointer-CAS admission inside the write transaction + pointer-dereferencing recovery reads with referential validation, and keep the recovery read shaped as `limit: 2` even though your pointer can only return 0/1 — the contract docstring is the porting boundary, and scan backends (memory/JSONL both delegate to one SessionState index) genuinely reach the 2+ arm. Adapt to backends without transactions: index over the replayed record stream, where corruption becomes detectable rather than impossible. Omit multi-row "open operation" tables unless you genuinely need concurrent per-lane operations; the single pointer is what makes the corruption state impossible.
