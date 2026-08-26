<!-- capsule-v2 -->
# Derived branch cache with copy-on-write — how do you make branch reads O(path) when entries form a tree, without ever letting the cache become truth?

**Source:** pi-upstream MIT `main@4af9d21d3b4d`; Codebase Memory `pi-upstream`. **Question:** How does a SQL session store materialize root-to-leaf conversation branches so reads never walk recursive parent chains, and how does appending to a mid-branch point avoid corrupting existing branches?

## Materialized path rows + tip pointers + prefix-copy on fork
**Path/Symbol:** `packages/session-backends/sqlite-node/src/sqlite/branch-cache.ts` (:14–101) and `storage/branch-entries.ts` (:39–174); schema comment `migrations/001_initial.sql:41-56`.
**Signature:** `appendEntryToBranchCache(db, sessionId, entryId, entrySeq, entryType, customType, parentId)`; `buildCachedBranch(db, sessionId, leafId)`; `rebuildBranchCache(db, sessionId)`.
**Data Shape:** `branch_entries(session_id, branch_id, entry_id, entry_seq, entry_type, custom_type)` — one FULL linear path per `branch_id`; `branch_tips(session_id, branch_id, tip_id)` PK(session_id,tip_id), UNIQUE(session_id,branch_id). Canonical parent links stay in `entries.parent_id`.

### Decisive source
```ts
const tipBranchId = readBranchTipBranchId(db, sessionId, parentId);
if (tipBranchId !== undefined) {
	extendBranch(db, sessionId, tipBranchId, parentId, entryId, entrySeq, entryType, customType);
	return;
}
const source = readBranchContainingEntry(db, sessionId, parentId);
if (!source) throw new SessionError("invalid_entry", `Branch cache has no branch containing parent entry ${parentId}`);
const branchId = uuidv7();
copyBranchEntriesThroughSeq(db, sessionId, branchId, source.branchId, source.entrySeq);
insertBranchEntry(db, sessionId, branchId, entryId, entrySeq, entryType, customType);
insertBranchTip(db, sessionId, entryId, branchId);
```
with `extendBranch` failing via optimistic tip update:
```ts
if (!updateBranchTip(db, sessionId, branchId, parentId, entryId)) {
	throw new SessionError("invalid_entry", `Branch tip ${parentId} changed during append`);
}
```

**Flow:** append resolves parent → parent is a live TIP: extend that branch in place and swing the tip (optimistic UPDATE returns changes≠1 if the tip moved) → parent is MID-branch: allocate a NEW branch_id, `INSERT … SELECT … WHERE entry_seq <= throughSeq` copies the prefix, then add the child + a new tip (copy-on-write; original branch untouched) → parent NULL: brand-new single-row branch → path builds (`insertBranchEntriesForPath`) walk parents leaf→root under a SAVEPOINT with cycle detection (`Entry parent cycle at X`) and per-custom-row payload parse for custom_type, inserting reversed root→leaf → rebuild deletes all cache rows and re-derives leaves via `NOT EXISTS (SELECT 1 FROM entries AS child … child.parent_id = leaf.id)` ordered by seq.
**Invariant:** the cache is always a DERIVED index — every mutation writes canonical `entries` first and cache rows in the same transaction, so crash-consistency reduces to SQLite atomicity; any cache loss is recoverable by rebuild, never by guesswork.
**Probe:** `packages/session-backends/sqlite-node/test/branch-cache.test.ts:15-42` — after compaction + lane move + re-append, raw SQL over `branch_entries` shows the branched child's branch contains exactly `[rootId, keptId, compactionId, branchedId]` (full root path); :83-115 proves missing cache fails BOTH read and write with `invalid_entry` ("has no branch containing parent entry").

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-upstream", name_pattern: ".*(buildCachedBranch|copyBranchEntriesThroughSeq|rebuildBranchCache)", limit: 10 });
```

## Verdict
Adopt: materialize full paths per branch, treat tips as optimistic pointers, fork mid-branch appends via seq-bounded prefix copy, keep parent links canonical and everything in one transaction. Adapt branch-id generation and savepoint scoping to your engine. Omit recursive-CTE read paths entirely — the materialization exists precisely so reads are flat scans. Coverage caveat: none on cited files (all `no_recorded_issue`).
