<!-- capsule-v2 -->
# Background manager chaining — how do per-retry memory/learning tasks avoid duplicate writes and leaked work?

**Source:** agno Apache-2.0 `main@9644f22982ae017eaa4ad85c561d927d9ac03119`; Codebase Memory `ext-agno`. **Question:** When a run retries, what happens to the memory/learning task the failed attempt already started?

## _astart_memory_task / _astart_learning_task
**Path/Symbol:** `libs/agno/agno/team/_managers.py:78` (memory; sync-future twin :115) and `:284` (learning; sync :249).
**Signature:** `async def _astart_memory_task(team, run_messages, user_id, existing_task: Optional[asyncio.Task]) -> Optional[asyncio.Task]`.
**Data Shape:** returns a NEW task each call or None when preconditions fail (`user_message` present ∧ `memory_manager` set ∧ `update_memory_on_run` ∧ NOT `enable_agentic_memory`); every worker returns an isolated `RunMetrics` collector that the caller merges at join time.

### Decisive source
```python
async def _astart_memory_task(team, run_messages, user_id, existing_task):
    # Cancel any existing task from a previous retry attempt
    if existing_task is not None and not existing_task.done():
        existing_task.cancel()
        try:
            await existing_task                       # absorb CancelledError HERE
        except asyncio.CancelledError:
            pass
    if (run_messages.user_message is not None and team.memory_manager is not None
            and team.update_memory_on_run and not team.enable_agentic_memory):
        return asyncio.create_task(_amake_memories(team, run_messages=..., user_id=...))
    return None

# spine side (_arun finally block):
if memory_task is not None and not memory_task.done():
    memory_task.cancel()
    try: await memory_task
    except asyncio.CancelledError: pass               # never leak an un-awaited task warning
```

**Flow:** attempt N starts workers → attempt fails → attempt N+1's start-helper cancels-and-AWAITS the old tasks BEFORE creating fresh ones → success path joins via `await_for_open_threads(memory_task, learning_task)` then `merge_background_metrics(run_response.metrics, collect_background_metrics(...))` → failure path's `finally` cancels any un-joined survivors.
**Invariant:** (1) Cancel must be FOLLOWED BY await — bare `.cancel()` leaves "Task was destroyed but it is pending!" warnings and can drop mid-write state. (2) Workers are started EARLY (right after messages exist) so memory extraction overlaps model latency; metrics from both paths merge into the response either way. (3) Agentic memory (`enable_agentic_memory`) and automatic background memory are mutually exclusive by precondition, not by error. (4) Each worker owns its metrics collector — no shared accumulator across retry attempts.
**Probe:** graph-resolves (`search_graph "adrain_member_tasks register_member_drain_task"` family; `_managers.py` Module node); behavior mirrored by upstream `tests/unit/team/test_team_learning.py` + `test_background_execution.py` executed GREEN in the 94-pass run.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-agno", query: "_astart_memory_task cancel existing", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt cancel-then-await chaining keyed on the previous attempt's handle; adapt worker bodies to your extraction logic; omit agno's RunMetrics plumbing. Caveat: sync path uses executor Futures with fire-and-forget cancel (no await equivalent) — weaker guarantee, noted for porters.
