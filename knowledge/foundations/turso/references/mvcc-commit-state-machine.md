<!-- capsule-v2 -->
# Commit state machine — why does each commit step precede the next?

**Source:** turso MIT `main@def9a060`; Codebase Memory `turso`. **Question:** When a commit spans async IO, what fixes the order of timestamp allocation, state publication, log write, and version rewrite?

## Transition ORDER is the correctness spec
**Path/Symbol:** `core/mvcc/database/mod.rs:1425-1483` (`enum CommitState`), ordering rationale comment block :3227-3262, end_ts/Preparing atomicity :2760-2795 region + `LogicalClock` contract in `core/mvcc/clock.rs:9-24`, monotonic header clock :3300-3345 (`fetch_max`, "an incorrect lower value can cause data loss / corruption" :3304).
**Signature:** `Initial → Commit{end_ts} → WaitForDependencies → BuildLogRecord → BeginCommitLogicalLog → WriteLogicalLog → SyncLogicalLog → EndCommitLogicalLog → CommitEnd → RewriteLiveVersions → FinalizeCommit`.
**Data Shape:** every state carries its `end_ts`; BuildLogRecord/RewriteLiveVersions carry a cursor and yield every `MVCC_COMMIT_BATCH_SIZE = 1024` rowids (:1514) — sized per comment "to keep a CREATE INDEX on a 2M-row table responsive".

### Decisive source
```rust
// mod.rs:3227-3237 (FinalizeCommit transition comments)
// (1) must precede (5): the commit lock serializes log writes ...
// (2) must precede (3): rewriting before marking Committed would
// publish the transaction's effects to readers before its fate is
// decided, which breaks rollback of abandoned commits.
// (2) must also precede (5): the next committer's validation ... checks our transaction state.
```
Two further ordered decisions: **end_ts allocation is atomic with Preparing publication**, both under the clock lock — closing the TOCTOU between "chose my timestamp" and "world can see me preparing"; and the global header timestamp only moves forward via fetch_max, because an older transaction can finish after a newer one and this value bounds checkpointing. The logical log records only the committing tx's contribution: own versions get begin = Timestamp(end_ts); versions this tx speculatively ended leave end unset because "tx_b will take care of logging the deletion"; schema rows serialize BEFORE data rows "so replay sees table_id_to_rootpage updates before row ops reference those ids". Abandonment has ONE choke point: `cleanup_unfinished_commit` (:1728) inspects observed state and either finishes or rolls back — including completing a mid-RewriteLiveVersions drop synchronously.

**Flow:** any step may hit disk ⇒ machine yields as IOResult::IO; resume re-enters at the same state; crash paths funnel through cleanup_unfinished_commit.
**Invariant:** reorder (2)/(3)/(5) and you get either published-but-abortable effects or mis-validated next committers; the comments are the spec, keep them beside the transitions.
**Probe:** tests.rs:2309 injects a yield at CommitValidation while a concurrent tx tombstones the row asserting serialization; tests.rs:2053 restarts the db and asserts the clock reseeds monotonically from the log; hermitage suite pins observable isolation across yields.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "turso", query: "CommitState RewriteLiveVersions FinalizeCommit", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the enumerated-state + documented-precedence pattern for any multi-step async commit. Adapt the IO plumbing (IOResult vs async/await). Omit the explicit Mutex<StateMachine> inside Checkpoint only if your runtime is truly single-threaded per connection.
