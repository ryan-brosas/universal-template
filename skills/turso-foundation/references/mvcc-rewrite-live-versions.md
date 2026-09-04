<!-- capsule-v2 -->
# MVCC rewrite-live-versions — how do committed TxID references become timestamps without blocking readers?

**Source:** turso MIT `main@def9a060`; Codebase Memory `turso`. **Question:** After Committed(ts) is published but before chains are rewritten, what lets readers resolve half-migrated state?

## Chunked in-place rewrite AFTER fate publication; readers consult txs[tx_id] meanwhile
**Path/Symbol:** `core/mvcc/database/mod.rs:1471-1482` (`RewriteLiveVersions(RewriteLiveVersionsCtx)` state + doc), ctx :1503-1509, chunk loop :2388/:2719 (`MVCC_COMMIT_BATCH_SIZE`), ordering guarantee (2)-before-(3) at :3231-3235, reader fallback documented at :1473-1475 ("readers consult `txs[tx_id]` to resolve any TxID references that haven't been rewritten yet").
**Signature:** state carries `{end_ts, cursor}`; each step processes ≤1024 write-set entries then yields as IO.
**Data Shape:** rewrite sets begin=Timestamp(end_ts) on created versions and clears/commits speculative ends; between chunks a version may show either encoding — both resolve identically via the now-Committed transaction record.

### Decisive source
```rust
// mod.rs:1477-1482 — FinalizeCommit transition comments:
// Hand off to the chunked rewriter. Between chunks readers
// resolve any unwritten TxID refs via `txs[tx_id]` which now
// reports Committed(end_ts).
// :3231-3234 — why rewrite must FOLLOW Committed publication:
// rewriting before marking Committed would publish the transaction's
// effects to readers before its fate is decided
```
The design point porters miss: rewriting is an OPTIMIZATION layered over correct resolution, not the correctness mechanism itself. Because visibility predicates already dereference TxIDs through the transaction table, the rewrite could even crash midway without corruption — cleanup_unfinished_commit (:1728) resumes it. Chunking exists purely to keep a 2M-row CREATE INDEX commit from monopolizing the executor.

**Flow:** CommitEnd {state=Committed} → RewriteLiveVersions {per-chunk in-place re-packs} → FinalizeCommit {drain deps, release lock, bump header clock, auto-checkpoint}.
**Invariant:** never rewrite before fate publication; every intermediate encoding must be resolvable by the standard predicate path; batch yields must be resumable from the cursor alone.
**Probe:** yield-injected commit tests around the RewriteLiveVersions boundary; drop-mid-rewrite case handled by cleanup_unfinished_commit (issue #7477 cited in-source).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "turso", query: "RewriteLiveVersions RewriteLiveVersionsCtx FinalizeCommit", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt publish-fate-then-migrate-lazily for any tagged-reference migration. Adapt chunk size to your executor. Omit the explicit cursor if your runtime supports true async.
