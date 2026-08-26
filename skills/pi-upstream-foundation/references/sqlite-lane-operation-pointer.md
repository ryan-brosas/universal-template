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

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-upstream", name_pattern: ".*(startLaneOperation|readOpenOperationRows)", limit: 10 });
```

## Verdict
Adopt: pointer-CAS admission inside the write transaction + pointer-dereferencing recovery reads with referential validation. Adapt to backends without transactions (the leaf's JSONL capsules scan for unmatched starts instead — same contract, scan-derived answer). Omit multi-row "open operation" tables unless you genuinely need concurrent per-lane operations; the single pointer is what makes the corruption state impossible.
