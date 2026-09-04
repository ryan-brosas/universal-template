<!-- capsule-v2 -->
# detached spawn (fire-and-forget with sole-launch-site discipline)

## Source
pipeshub-ai Apache-2.0 `main@4a02110d`; Codebase Memory `pipeshub-ai`. **Question:** How does a spawn_agent call return immediately while its child still lands its result where later `depends_on` references can find it — and how do you guarantee exactly ONE child launches?

## Path/Symbol
`tools/builtin/coordination/spawn_agent.py` — `_run_detached_spawn(agent, call, goal, turn_index, started_at)` (:140–191), detach branch of `SpawnAgentTool.handle()` (:322–337), `agent._detached_tasks` bookkeeping. Launch-site contract in `agent/__init__.py`'s `spawn_calls` filter.

## Signature
`handle()` detach branch: timeline entry → `asyncio.create_task(_run_detached_spawn(...))` → add to `agent._detached_tasks` → returns IMMEDIATELY: `{"detached": True, "note": "Sub-agent launched in the background. Its result will appear in the timeline/events later, not as a tool_result in this turn."}`.

## Data Shape
Background body: `task_id = raw_task_id(call)`; success or infrastructure failure BOTH end in `record_completed_spawn(agent.scope, task_id, result)` (failure synthesizes an AgentResult with the error string :178–189); finally: `agent._detached_tasks.discard(asyncio.current_task())`.

### Decisive source
```python
This is the ONLY place a `detach=true` call's child ever gets
launched — `Agent.step()`'s `spawn_agent` pre-launch batch excludes
detached calls specifically so `handle()` below never launches a
SECOND child for the same call (see `agent/__init__.py`'s
`spawn_calls` filter). The completion is still recorded into
`SPAWN_RESULTS_SLOT` (same as a scheduled spawn) so a `depends_on`
from a LATER turn can reference this task_id once it lands.
```

**Flow:** detach=true → parent continues same turn → child runs on its own task (never on the parent's turn loop) → completion lands via SPAWN_RESULTS_SLOT + timeline + TOOL_RESULT event (`[detached]` prefix) → a later turn's depends_on resolves against the slot exactly as for scheduled spawns.

**Invariant:** Sole-launch-site: step-level pre-launch EXCLUDES detached calls, handle() is their only launcher — two launch sites = two children for one call. Failure must still record into the slot (a waiting dependent would otherwise hang forever). Deferred import of spawn_scheduler (:152–155): module-level import would be circular (spawn_scheduler imports graph_utils; tools/builtin/__init__ imports THIS module).

**Probe:** `tests/unit/agent_loop_lib/agent/test_spawn_agent_detach.py` — exactly-one-child :71–102 (one detached task, one extra LLM call, slot recorded), failure-recorded-for-dependents :115+.

## Get live surrounding code
**Retrieve:**
```bash
codebase-memory-mcp cli search_graph --project pipeshub-ai --semantic-query '["_run_detached_spawn","SPAWN_RESULTS_SLOT","_detached_tasks"]'
```

## Verdict
Adopt fire-and-forget-with-slot-recording and the single-launch-site invariant; adapt task-set bookkeeping to host's agent object.
