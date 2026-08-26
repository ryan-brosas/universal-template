<!-- capsule-v2 -->
# Time-travel fork ladder — How does replay from an old checkpoint avoid corrupting the live thread?

**Source:** LangGraph MIT `main@f09cfe8ffc1eeffd68f4b628ed69c30f7cad229f`; Codebase Memory `ext-langgraph`. **Question:** When is a resume NOT a resume — and what must be dropped or forked before replaying?

## is_resuming vs is_time_traveling; stale RESUME/INTERRUPT writes are poison
**Path/Symbol:** `libs/langgraph/langgraph/pregel/_loop.py:PregelLoop._first` (:848-1080; resume detection :861-870, time-travel gate :872-899, fork checkpoint :952-971).
**Signature:** `_first(*, input_keys, updated_channels: set[str] | None) -> set[str] | None`.
**Data Shape:** Decision inputs: `checkpoint["channel_versions"]` non-empty (prior run exists), input shape (None / Command / dict), CONFIG_KEY_RESUMING (set by parents), run_id equality with checkpoint metadata, is_replaying flag (explicit checkpoint_id requested).

### Decisive source
```python
# When replaying from a specific checkpoint, drop cached RESUME
# writes so that interrupt() calls re-fire instead of returning
# stale values. But if we're actively resuming, keep them —
# multi-interrupt scenarios need previously resolved values preserved.
is_time_traveling = self.is_replaying and (
    (self.is_nested and ns in configurable.get(CONFIG_KEY_CHECKPOINT_MAP, {}))
    or not ((input_is_command and cmd.resume is not None)
            or configurable.get(CONFIG_KEY_RESUMING, False))
)
if is_time_traveling:
    self.checkpoint_pending_writes = [w for w in ... if w[1] != RESUME]
...
if is_time_traveling and self.checkpoint_metadata.get("source") not in ("update", "fork"):
    # Clear old INTERRUPT writes ... The fork will have a new checkpoint_id
    # which changes task IDs — stale interrupt writes would accumulate ...
    self.checkpoint_pending_writes = [w for w in ... if w[1] != INTERRUPT]
    self._put_checkpoint({"source": "fork"})
```
**Flow:** Resume inference ladder: parent flag → None input (invoke(None)) → Command input → same-run_id re-entry. Time-travel = replaying AND NOT actually resuming. On time travel: drop RESUME writes (interrupts must re-fire), clear INTERRUPT writes, persist a `{"source": "fork"}` checkpoint so subsequent execution branches instead of overwriting head — without it, an interrupt-before-after_tick would leave the OLD checkpoint as latest and later resumes load wrong state. Subgraphs receive CONFIG_KEY_REPLAY_STATE (ReplayState with before-bound id) only when truly time traveling; Studio-style `{checkpoint_id} + Command(resume)` at head stays normal-resume.

**Invariant:** update/fork-source checkpoints already ARE forks — skip re-forking them. Fork checkpoints get fresh ids ⇒ deterministic task ids change ⇒ old task-scoped writes can't leak into the replayed branch. The values stream still emits current state on resume so clients see where they resumed from.

**Probe:** `grep -n 'is_resuming = bool' libs/langgraph/langgraph/pregel/_loop.py` → :861; `grep -n 'w\[1\] != RESUME\|w\[1\] != INTERRUPT' libs/langgraph/langgraph/pregel/_loop.py` → :899/:969; `grep -n '"fork"' libs/langgraph/langgraph/pregel/_loop.py | head -3` → :962/:1060. Direct tests: `tests/test_pregel.py:3326 test_subgraph_checkpoint_true_interrupt`, `:7418 test_interrupt_subgraph_reenter_checkpointer_true`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-langgraph", query: "_put_exit_delta_writes", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the two-axis decision (resuming vs replaying) and mandatory-fork-on-replay rule for any durable engine with branching history. Adapt the source-tag vocabulary to your metadata schema. Omit ReplayState plumbing if your host has no subgraph checkpoint maps.
