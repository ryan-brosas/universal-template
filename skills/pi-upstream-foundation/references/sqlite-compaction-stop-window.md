<!-- capsule-v2 -->
# Compaction stop-boundary windowing — how does a branch read return only "since the last compaction" and stay immune to corrupt payloads outside that window?

**Source:** pi-upstream MIT `main@4af9d21d3b4d`; Codebase Memory `pi-upstream`. **Question:** How do you slice a materialized branch at the last stop-entry (compaction) in SQL, and why must payload decoding happen only after the window is selected?

## Correlated MIN/MAX boundary, inclusive; decode after selection; validate chain on full reads
**Path/Symbol:** `packages/session-backends/sqlite-node/src/sqlite/storage/branch-entries.ts:queryCachedBranchRows` (:49–94); validators in `repo.ts:validateCachedBranchRows` (:292–310) and `decodeEntry` (:190–266).
**Signature:** `queryCachedBranchRows(db, sessionId, branch: {branchId, leafSeq}, query: CachedBranchQuery): CachedBranchEntryRow[]`.
**Data Shape:** query carries optional `stopAtType` / `stopAtId`, cursor `{afterSeq}`, order, limit. Rows join cache membership back to canonical `entries`.

### Decisive source
```ts
const boundary =
	stopPredicates.length === 0
		? sql``
		: sql`SELECT ${aggregate}(stop.entry_seq)
			FROM branch_entries AS stop
			WHERE stop.session_id = ${sessionId}
				AND stop.branch_id = ${branch.branchId}
				AND stop.entry_seq <= ${branch.leafSeq}
				AND (${joinSqlFragments(stopPredicates, " OR ")})`;
...
if (stopPredicates.length > 0) {
	predicates.push(
		sql`b.entry_seq ${boundaryComparison} COALESCE((${boundary}), ${oldestFirst ? branch.leafSeq : 0})`,
	);
}
```

**Flow:** caller (test helper `getSqliteBranch` mirrors production) asks `{ start: leafId, stopAtType: "compaction" }` → boundary subquery picks MIN(entry_seq) of matching stop-rows at-or-before the leaf for oldest-first reads → main scan filters rows to `entry_seq <= boundary` INCLUSIVE (the compaction entry itself ships with its summary) → COALESCE keeps the whole path when no stop-row exists → rows are joined to entries and ONLY THEN mapped through strict `decodeEntry` (per-type payload validation raising `SessionError("invalid_entry", "Invalid SQLite session entry …")`). On unfiltered unbounded reads `validateCachedBranchRows` additionally re-checks parent-chain continuity of the returned rows (`Entry X not found`) — catching cache↔canonical drift.
**Invariant:** selection precedes decoding. A payload corrupted OUTSIDE the requested window can never fail a windowed read; conversely a tampered canonical parent graph is detected by row validation rather than silently served.
**Probe:** `packages/session-backends/sqlite-node/test/branch-cache.test.ts` — :44-66 sets one old entry's payload to `"not json"` then reads the compaction window successfully (`[compactionId, leafId]`); :172-196 rewires an entry's `parent_id` and asserts `findEntriesOnBranch` rejects `invalid_entry`.

## Direct test witnesses — validation scope equals window scope
**Path/Symbol:** `packages/session-backends/sqlite-node/test/branch-query.test.ts` (whole file, 139 lines, read this pass); strict-decode loudness also pinned at `test/repository.test.ts` :326–347 (corrupted entry payload ⇒ `invalid_entry`) and :349–377 (corrupted record payload ⇒ `storage` "failed to decode payload").
**Signature:** all three cases drive `session.findEntriesOnBranch` after raw-SQL tampering of `entries.payload`, `entries.parent_id`, or `branch_entries` rows.

Three upstream cases pin what the SQL twin implies:
1. **"does not decode entries outside bounded branch queries"** — middle entry's payload set to `"not json"` AND its `branch_entries` cache row deleted: `{start: leafId, stopAtId: leafId}` → `[leafId]` and `{start: leafId, stopAtId: rootId, order: "oldestFirst", limit: 1}` → `[rootId]` both succeed; `{start: leafId, limit: 2}` rejects `invalid_entry` "Entry middleId not found" (the deleted cache row breaks the UNBOUNDED walk).
2. **"does not decode entries excluded by branch query filters and limits"** — custom entry's payload set to `{}` (valid JSON, wrong shape): `{type: "message", limit: 1}` → `[leafId]`; payload then set to `"not json"`: `{customType: "other"}` → `[]` — filter-excluded rows are never decoded, even into invalid JSON.
3. **"does not validate ancestors beyond newest-first stop bounds"** — child's `parent_id` tampered to `"missing-parent"`: bounded reads (`{stopAtId: childId}`, `{stopAtType: "message"}`) return `[childId]` without touching the parent chain; unbounded `{start: childId}` rejects `invalid_entry` "Entry missing-parent not found". Then a root↔child parent CYCLE (both parents rewritten): bounded reads still fine; unbounded rejects "Entry childId not found" — the cycle guard terminates the walk and reports the re-encountered entry as missing.

**Invariant (added):** validation scope == window scope. Bounded reads are blind to payload corruption AND parent-graph tampering outside the window; only unbounded reads run chain validation, and the cycle guard converts infinite walks into `invalid_entry` instead of hangs.
**Probe:** deterministic probe P4 executed this pass (verification.md): transcribed boundary SQL + cycle-guarded walk on a tampered fixture reproduces all three case outcomes (one honest probe correction recorded — the cycle case requires rewriting BOTH parents, matching the test).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.get_code_snippet({ project: "pi-upstream", qualified_name: "pi-upstream.packages.session-backends.sqlite-node.src.sqlite.storage.branch-entries.queryCachedBranchRows" });
```

## Verdict
Adopt: SQL-level stop boundary computed from the same table being scanned, inclusive of the stop entry, decode strictly post-selection, plus a continuity validator on unbounded reads as the drift alarm. Adapt aggregate/comparison polarity to your ordering convention (MIN/`<=` oldestFirst vs MAX/`>=` newestFirst). Omit application-side window filtering — doing decode-before-selection reintroduces the corruption blast radius this design removes. Port the bounded-vs-unbounded validation split as a TEST, not just a behavior: the three branch-query cases above are the executable spec.
