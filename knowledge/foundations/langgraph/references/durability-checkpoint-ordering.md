<!-- capsule-v2 -->
# Durability modes & checkpoint ordering — When does state hit the checkpointer, and what guarantees write-before-checkpoint visibility?

**Source:** LangGraph MIT `main@f09cfe8ffc1eeffd68f4b628ed69c30f7cad229f`; Codebase Memory `ext-langgraph`. **Question:** How do sync/async/exit durability differ, and how are checkpoint puts ordered against task-write puts?

## Chained put_after_previous futures; delta writes drain BEFORE the next checkpoint
**Path/Symbol:** `libs/langgraph/langgraph/pregel/_loop.py:_put_checkpoint` (:1081-1219), `_put_pending_writes` (:510-549), `_put_exit_delta_writes` (:1221-1315), `_suppress_interrupt` (:1317-1379), durability plumbing in `main.py:Pregel.stream` (`if durability_ == "sync": loop._put_checkpoint_fut.result()`).
**Signature:** `_put_checkpoint(metadata)` — gates on `exiting = metadata is self.checkpoint_metadata` (identity, not equality).
**Data Shape:** Durability ∈ {"sync", "async", "exit"}; `_delta_write_futs: list` collects futures for DeltaChannel writes; `_error_handler_write_futs` likewise for handler markers; exit accumulator `_exit_delta_writes: list[(step, tid, chan, val)]`.

### Decisive source
```python
# save it, without blocking
# if there's a previous checkpoint save in progress, wait for it
# ensuring checkpointers receive checkpoints in order
self._put_checkpoint_fut = self.submit(
    self._checkpointer_put_after_previous,
    getattr(self, "_put_checkpoint_fut", None),
    self.checkpoint_config,
    copy_checkpoint(self.checkpoint),
    self.checkpoint_metadata,
    new_versions,
)
```
**Flow:** Per superstep after apply_writes → `_put_checkpoint({"source": "loop"})`. Each put SUBMITS a future that first AWAITS the previous put's future ⇒ strict ordering regardless of executor scheduling. Task-level `put_writes` fire-and-forget under sync/async (skipped under exit). Exit mode: intermediate steps do NOT checkpoint; at loop exit `_suppress_interrupt` runs `_put_exit_delta_writes()` → final `_put_checkpoint(self.checkpoint_metadata)` (identity-flagged: skips counter double-count, reuses saved id) → `_put_pending_writes()`. The sync driver additionally blocks on `_put_checkpoint_fut.result()` each iteration so "sync" truly persists before the next step starts. Delta-channel invariant enforced by draining `_delta_write_futs` before the next checkpoint put — "a checkpoint never becomes durable before the writes that produced it."

**Invariant:** Exit-mode delta writes need an anchor parent; on a childless thread a lazy STUB checkpoint (id = checkpoint_id_saved, metadata step=-2) is created so writes have somewhere to hang. Synthetic exit task ids embed the superstep as the first UUID group (`{step:08d}-{rest}`) so savers' `ORDER BY task_id, idx` preserves chronological replay order while remaining valid UUIDs. Overwritten delta channels force-snapshot with a MANUAL version bump when apply_writes didn't bump them (else the snapshot blob would be silently dropped by saver new_versions filtering).

**Probe:** `grep -n 'exiting = metadata is self.checkpoint_metadata' libs/langgraph/langgraph/pregel/_loop.py` → :1092; `grep -n 'step:08d' libs/langgraph/langgraph/pregel/_checkpoint.py` → :47. Direct tests: `tests/test_delta_channel_exit_mode.py:26 test_exit_delta_task_id_is_valid_uuid_and_ordered` (asserts id1 < id7 and group split), `tests/test_pregel.py:5372 test_checkpoint_recovery` (durability-parametrized).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-langgraph", query: "_put_checkpoint", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt futures-chained ordered puts + write-before-checkpoint draining for any async persistence layer. Adapt durability vocabulary and stub mechanics to your saver API. Omit the exit-accumulator if your host has no deferred-durability mode.
