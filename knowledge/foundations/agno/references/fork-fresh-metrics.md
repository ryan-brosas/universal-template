<!-- capsule-v2 -->
# Fork resets fresh-run accumulators — Why does a forked run need its metrics/events/timer wiped?

**Source:** agno Apache-2.0 `main@9644f22982ae017eaa4ad85c561d927d9ac03119`; Codebase Memory `ext-agno`. **Question:** What lineage-irrelevant state must a fork NOT inherit from its source run?

## Deep-clone then reset metrics/timer/created_at/events
**Path/Symbol:** `libs/agno/agno/agent/_run.py:_fork_run` (:3029-3070).
**Signature:** `_fork_run(run_response: RunOutput, message_index: int) -> RunOutput`.
**Data Shape:** returns a NEW RunOutput (deepcopy); original untouched; same session_id (sibling run).

### Decisive source
```python
forked = copy.deepcopy(run_response)
forked.run_id = str(uuid4())
forked.forked_from_run_id = run_response.run_id
forked.forked_from_message_index = message_index
# Reset lineage-irrelevant accumulators so the fork reports its own work,
# not the parent's. Without this, token counts and durations double-count,
# and (with store_events=True) the fork's events list would be the parent's
# events with the new run's events appended onto it.
forked.metrics = RunMetrics()
forked.metrics.start_timer()
forked.created_at = int(_time())
forked.events = None
_truncate_run_to_checkpoint(forked, message_index)
```

**Flow:** snap boundary → deepcopy → mint new run_id + lineage fields → reset accumulators → start the fork's OWN timer (the continue path never starts one, so without this RunCompleted events carry no duration) → truncate the clone.
**Invariant:** A fork is a new RUN, not a continuation: token counts, durations, birthtime, and event lists are per-run ledgers. Inheriting them double-counts usage and corrupts event streams (parent events + child events appended). Only identity lineage (`forked_from_*`) crosses the copy.
**Probe:** `grep -c 'forked.metrics = RunMetrics()' libs/agno/agno/agent/_run.py` → **1**; direct behavior tests `libs/agno/tests/unit/agent/test_unified_continue.py::TestForkHelper` (:855) incl. `test_fork_at_mid_batch_index_is_pair_safe`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-agno", query: "_fork_run forked_from_run_id deepcopy", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the reset list as the canonical "new-run accumulator" checklist whenever cloning run state; adapt metric field names; omit timer start if your completion events derive duration differently.
