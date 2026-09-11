<!-- capsule-v2 -->
# MVCC schema checkpointing — how do table-id→rootpage bindings survive a crash mid-materialization?

**Source:** turso MIT `main@def9a060`; Codebase Memory `turso`. **Question:** When MVCC tables get real B-tree root pages during checkpoint, what keeps the mapping atomic for both replay and live readers?

## Staged RootMapOps published in one window + negative canonical table ids
**Path/Symbol:** `core/mvcc/database/checkpoint_state_machine.rs:137-145` (`enum RootMapOp { Alloc{id,root}, SetEnd{...}, ...}` "Root-map mutation staged during collection; applied in the publish window"), SQLITE_SCHEMA_ROOT_PAGE = 1 (:52-53), schema-row-first log ordering (mod.rs:1492-1495: "Schema rows are emitted first so log replay sees CREATE TABLE before related INSERTs"), id canonicalization to negative root-page numbers.
**Signature:** collection phase records `RootMapOp`s; a single publish window applies them after durability boundaries are set.
**Data Shape:** binding triple (MVTableId → root page u64 | dropped-end-ts); the meta sidecar row (`__turso_internal_mvcc_meta`) rides in the same pager transaction.

### Decisive source
```rust
// checkpoint_state_machine.rs:137-140:
// /// Root-map mutation staged during collection; applied in the publish window.
// enum RootMapOp {
//     /// Insert a new (checkpointed) root binding for `id` at `root` (STAGED → published).
//     Alloc { id: MVTableId, root: u64 },
//     /// Set the `end` ts of `id`'s binding (DROP of a checkpointed object).
```
Two-phase (stage → publish) means a mid-collection yield leaves readers on the OLD consistent map; the publish window is the only place bindings change, and it sits after the durable boundary so replay never sees a binding whose data didn't make it. Log-side ordering complements this: schema ops precede data ops in every frame, and table ids encode as negative root pages "so recovery bootstraps cleanly" (mod.rs BuildLogRecord docs) — the sqlite_schema tree at page 1 anchors everything else.

**Flow:** collect rows per table → stage Alloc/SetEnd ops → commit pager txn (data + meta + bindings atomically) → publish → GC can now reclaim version-store copies below LWM.
**Invariant:** bindings change in ONE window only; a published binding's backing pages are always already durable; drops record an end-ts rather than deleting history (MVCC discipline extends to catalog objects).
**Probe:** forced-yield checkpoints (`AfterCollectTableRows`, `BeforePagerCommit`) assert resumption with staged-but-unpublished maps; restart probes assert clock/binding coherence.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "turso", query: "RootMapOp sqlite_schema rootpage checkpoint", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt staged-binding publication for any engine materializing logical objects onto physical structures. Adapt staging container to your state machine. Omit drop-tombstones unless your catalog is itself versioned.
