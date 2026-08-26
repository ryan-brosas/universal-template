<!-- capsule-v2 -->
# Errored-field update gating — which broken computed columns still get written, and why?

**Source:** teable AGPL `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** How does UPDATE...FROM SELECT decide its SET column list when some computed fields are in error states?

## getUpdatableColumns / getReturningColumns
**Path/Symbol:** `apps/nestjs-backend/src/features/record/computed/services/record-computed-update.service.ts:RecordComputedUpdateService.getUpdatableColumns` (:482–520), `getReturningColumns` (:522–562), `updateFromSelect` (@retryOnDeadlock :583–627).
**Signature:** `getUpdatableColumns(fields): string[]` (dbFieldNames for SET); `updateFromSelect(tableId, qb, fields, opts?): Promise<Row[]>`.

### Decisive source
```ts
// Skip fields currently in error state to avoid type/cast issues — except for           // :491
// lookup/rollup (and lookup-of-link) which we still want to persist so they
// get nulled out after their source is deleted. Query builder emits a typed
// NULL for errored lookups/rollups ensuring safe assignment.
const isRollup = f.type === FieldType.Rollup || f.type === FieldType.ConditionalRollup;
if (hasError && !isLookupStyle && !isRollup) { /* formulas: keep unless generated */ }
...
// Acquire row-level locks in a deterministic order to avoid deadlocks when multiple      // :607
// computed updates touch the same set of records concurrently.
await this.lockRestrictRecords(tableId, dbTableName, restrictRecordIds);
```

**Flow:** SET list excludes errored fields EXCEPT lookup-style and rollups (they must persist typed NULLs to clear stale values once sources vanish) and non-generated formulas (regular columns get explicit NULL-out). Audit fields: track-all timestamps stay in RETURNING even when generated (:530–536) but generated audit USERS are skipped (:537–539); lookup-formulas return by physical column; non-lookup generated formulas return via generated name only when not errored. Locks acquired BEFORE the UPDATE...FROM SELECT whenever restrictRecordIds exist; whole call wrapped in @retryOnDeadlock.
**Invariant:** The query builder must emit TYPED nulls (`CAST(NULL AS jsonb)` etc.) for errored lookups — plain NULL breaks PG type inference in multi-row UPDATE...FROM. Deterministic lock order + sorted ids upstream = deadlock-free concurrent recomputes.
**Probe:** needles verified at this pin (:44 comment anchor, :160 lock-order comment); graph retrieval `updateFromSelect` resolves :584–627; coverage `no_recorded_issue` ×2 paths.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "getUpdatableColumns", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the errored-class matrix (lookup/rollup persist nulls; formulas skip unless regular columns); adapt ts-pattern match arms to plain predicates; omit decorator retry if your framework lacks it (wrap manually).
