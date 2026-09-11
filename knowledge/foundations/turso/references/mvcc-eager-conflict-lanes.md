<!-- capsule-v2 -->
# MVCC upsert/delete eager-conflict lanes — which write paths bypass the deferred sweep, and what does that mean for porters?

**Source:** turso MIT `main@def9a060`; Codebase Memory `turso`. **Question:** Beyond the commit-time validation ladder, exactly WHICH operations fire `WriteWriteConflict` immediately, and why does the asymmetry matter?

## Plain UPDATE/DELETE probe eagerly; INSERT stays pure; UPSERT paths can bypass
**Path/Symbol:** `core/mvcc/database/mod.rs:5245-5256` (delete path: visibility-first then `is_write_write_conflict` with `turso_assert_reachable!("write-write conflict on delete")`), index twin :5209-5216, insert exemption :5011-5013, predicate :9785-9821.
**Signature:** `delete_from_table_or_index(...)` → per visible version: `if is_write_write_conflict(...) { return Err(LimboError::WriteWriteConflict); }`.
**Data Shape:** the eager check consults ONLY versions visible to the deleting tx ("A transaction cannot delete a version that it cannot see, nor can it conflict with it") — invisible history can never eagerly conflict.

### Decisive source
```rust
// hermitage_tests.rs:14-18 pins WHY the lanes differ:
//   - Write-write conflicts are detected immediately at write time (WriteWriteConflict),
//     NOT deferred to commit (like FoundationDB)
// tests.rs evidence cited in-repo: plain UPDATE eagerly detects conflicts via
// delete_from_table_or_index (:14666 region); UPSERT paths can bypass eager
// detection (:14857 region) because upsert = delete+insert and the delete half
// may find nothing visible while the insert half stays optimistic by design.
```
Porter's consequence: error TIMING differs by statement shape. A plain UPDATE against a row another committed tx touched fails at the UPDATE; an upsert of the same row may sail through both halves optimistically and only fail (or win) in the commit sweep. Both are correct under first-committer-wins, but applications observe different failure points — a behavioral contract your port inherits whether you document it or not.

**Flow:** DELETE/UPDATE {reverse scan → visible? → conflict predicate → Err now} | INSERT {no check} | UPSERT {best-effort eager on the delete half} → all paths → commit sweep as backstop for what eagerness missed.
**Invariant:** eager checks never fire on invisible versions; the commit sweep remains authoritative for every path; changing lane placement changes observable error timing (hermitage-pinned).
**Probe:** hermitage suite `test_hermitage_write_write_conflict` + `test_hermitage_p4_lost_update`; staged probes tests.rs:14666/:14857/:14887/:14943.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "turso", query: "is_write_write_conflict delete_from_table_or_index upsert", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt lane-for-lane (eager delete/update, optimistic insert) if you want drop-in behavioral parity; otherwise pick ONE lane and adjust the hermitage matrix accordingly. Never ship mixed lanes without documenting error-timing differences.
