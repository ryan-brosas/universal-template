<!-- capsule-v2 -->
# Session-state branch windowing — how does the in-memory scan backend implement stop-boundary windows so it matches the SQL aggregate twin in BOTH directions?

**Source:** pi-upstream MIT `main@4af9d21d3b4d`; Codebase Memory `pi-upstream`. **Question:** The contract says a branch scan "ends after the first match, inclusive" — but first in which direction? How do you implement `findEntriesOnBranch` stop-bounds in a scan backend so memory/JSONL and SQLite return identical windows for newestFirst AND oldestFirst?

## Direction-dependent first-match-inclusive; one scan path serves two backends
**Path/Symbol:** `packages/agent/src/harness/session/state.ts:findEntriesOnBranch` (:198–215) + `walkToRoot` (:301–320); contract docstring `types.ts:BranchBounds.stopAtType` (:234); SQL twin `packages/session-backends/sqlite-node/src/sqlite/storage/branch-entries.ts:queryCachedBranchRows` (:49–94).
**Signature:** `findEntriesOnBranch(query: EntryQuery & BranchBounds & { start: string }): Entry[]`; `walkToRoot(start: string | null, bounds?: Pick<BranchBounds, "stopAtId" | "stopAtType">): IterableIterator<Entry>`.
**Data Shape:** BOTH the memory backend (`memory.ts:100`) and the JSONL backend (`jsonl/storage.ts:203`) delegate to this one method wrapped in `structuredClone` — so the "scan-derived" side of the JSONL↔SQLite divergence is a single code path. SQLite computes the same boundary with correlated `MIN`/`MAX(entry_seq)`.

### Decisive source
```ts
if (query.order === "oldestFirst") {
	for (const entry of [...this.walkToRoot(query.start)].reverse()) {
		const reachedBound = entry.id === query.stopAtId || entry.type === query.stopAtType;
		if (this.matchesEntryQuery(entry, query)) results.push(entry);
		if (reachedBound || results.length === query.limit) break;
	}
} else {
	for (const entry of this.walkToRoot(query.start, query)) {
		if (this.matchesEntryQuery(entry, query)) results.push(entry);
		if (results.length === query.limit) break;
	}
}
```
```ts
// walkToRoot — bounds stop the walk AFTER yielding the stop entry (inclusive)
if (current.id === bounds?.stopAtId || current.type === bounds?.stopAtType || current.parentId === null) break;
```
```ts
// types.ts:234 — the shared contract
stopAtType?: Entry["type"]; // scan ends after the first match, inclusive
```

**Flow:** newestFirst passes `bounds` into `walkToRoot`, which stops after yielding the NEWEST matching stop-entry; oldestFirst materializes the FULL path (walk WITHOUT bounds), reverses to root→tip, and breaks after pushing the OLDEST matching stop-entry. SQLite mirrors this exactly: `MIN(entry_seq)` boundary with `entry_seq <= COALESCE(boundary, leafSeq)` for oldestFirst, `MAX(entry_seq)` with `>= COALESCE(boundary, 0)` for newestFirst. Both sides include the stop entry itself and both fall back to the whole path when no stop-row exists.
**Invariant:** "first match" means first IN SCAN DIRECTION. A porter who implements "stop at the last compaction" unconditionally gets newestFirst right and silently breaks oldestFirst pagination (window anchored at the oldest compaction instead). Cycle guard (`visited` set ⇒ `invalid_entry`) and missing-parent detection (`invalid_entry`) live in the walk, not the caller.
**Probe:** conformance case "supports bounded filtered and cursor-based queries" (`packages/agent/src/harness/session/testing/conformance.ts:250-306`) pins the direction dependence across ALL backends on branch root→old-note(custom)→compact(compaction)→new-note(custom)→tail(message): `{start:"tail", stopAtType:"compaction", type:"message"}` ⇒ `[tail]`; `{start:"tail", stopAtId:"tail", type:"custom"}` ⇒ `[]` (stop at start itself, inclusive); `{start:"tail", stopAtType:"custom", order:"oldestFirst"}` ⇒ `[root, old-note]` (stops at the OLDEST custom — new-note excluded).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-upstream", name_pattern: ".*(findEntriesOnBranch|walkToRoot).*", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt: one scan implementation shared by every non-SQL backend (delegate + clone at the storage boundary), direction-dependent bound handling with the stop check placed AFTER the push (inclusive), and the contract sentence "scan ends after the first match, inclusive" written into the query type so both twins are held to the same words. Adapt nothing structural when adding a third backend: implement the MIN/MAX aggregate twin and let the shared conformance cases prove equivalence. Omit per-backend window logic entirely — it is how the two directions drift apart. Caveat: MCP graph was not connected this pass; anchors verified by direct read at pin `4af9d21d`, and the scan twin vs SQL twin were re-executed side by side against the conformance fixture (probe P3 GREEN 6/6 — identical windows on all four cited queries plus both no-stop full paths).
