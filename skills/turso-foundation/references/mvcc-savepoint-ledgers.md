<!-- capsule-v2 -->
# MVCC savepoints — how do you roll back to a mid-transaction marker without breaking the outer transaction's write set?

**Source:** turso MIT `main@def9a060`; Codebase Memory `turso`. **Question:** What bookkeeping lets ROLLBACK TO SAVEPOINT undo some writes while keeping the transaction alive and its later writes intact?

## Created/deleted version-id ledgers with conditional write-set pruning
**Path/Symbol:** `core/mvcc/database/mod.rs:6830-6900` region (savepoint tracking), built on `record_created_table_version` / `record_deleted_table_version` / index twins (:5005-5015, :5247-5251) and canonical-Arc key dedup (:5000-5004).
**Signature:** savepoints snapshot the created/deleted ledgers; rollback restores versions BY ID — retain created versions that postdate nothing? No: RETAIN created versions listed before the savepoint, clear `end` on deletions recorded after it, and prune write-set entries ONLY when no surviving uncommitted version remains.
**Data Shape:** per-tx ledgers of (table|index, key, version_id); keys are canonicalized through the SkipMap's Arc ("returns the canonical Arc (ours on miss, an existing one on hit), which we hand to savepoint tracking") so id-based retention matches identity, not string equality.

### Decisive source
```text
// mod.rs:6830-6900 region — summarized contract (legacy leaf prose verified at def9a060):
// savepoints track created/deleted version ids; rollback-to:
//   1. versions CREATED after the savepoint become (None, None) invisible garbage
//      (the ordinary GC sweep reclaims them — no surgical chain edits);
//   2. rows DELETED after the savepoint simply lose their end timestamp,
//      undoing the deletion in place (Hekaton §2.4 style);
//   3. a write-set entry is pruned only when NO surviving uncommitted
//      version remains behind it.
```
Rule 3 is the subtle one: a row both created and deleted after the savepoint leaves an empty chain — safe to prune from the write set; a row with any surviving uncommitted version must stay because commit-time conflict validation still needs to scan it.

**Flow:** mark savepoint {copy ledgers} → more writes → rollback-to {in-place invalidate post-marker versions; restore ends; prune empty write-set rows} → transaction continues committing normally.
**Invariant:** never surgically remove chain nodes (GC owns reclamation); savepoint restore must operate on version IDs captured at mark time, not re-derived predicates.
**Probe:** tests.rs:10441-region behavior (rollback leaves `(None,None)` bounds while SkipMap slots persist) extends to savepoint granularity via hermitage-style staged writes; direct coverage caveat: dedicated savepoint tests live in the 20k-line tests module — pin by `savepoint` symbol search when running.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "turso", query: "savepoint record_created_table_version write_set rollback", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt ledger-based savepoints over copy-on-write snapshots for memory-bounded partial rollback. Adapt ledger shape to your version store. Omit index-ledger mirroring until you port index versioning.
