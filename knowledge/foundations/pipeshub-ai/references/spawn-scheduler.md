<!-- capsule-v2 -->
# Dependency-aware spawn scheduling — how do parallel spawn_agent calls get enforced (not suggested) ordering, cross-turn?

**Source:** pipeshub-ai Apache-2.0 `main@4a02110d`; Codebase Memory `pipeshub-ai`. **Question:** How do you launch a batch of sub-agent spawns so `depends_on` children wait for prerequisite output — with invalid batches rejected per-call and orphans impossible?

## Validate pure → launch all → await slots → cancel in finally
**Path/Symbol:** `backend/python/app/agent_loop_lib/agent/spawn_scheduler.py` — module docstring (1-45), `_DEPENDENCY_RESULT_CHAR_CAP = 24_000` (:84), `SPAWN_RESULTS_SLOT` StateSlot (:112-114), `validate_spawn_batch` (:233-314), `_smart_truncate` (:317-339), `_format_dependency_section` (:384-407), `_augment_goal` (:410-414), `_run_dependent_spawn` (:417-494), `cancel_pending_spawn_tasks` (:501-519), `schedule_spawn_batch` (:522-600).
**Signature:** `async def schedule_spawn_batch(agent, runtime, spawn_calls, run_scope, *, goal, turn_index, started_at) -> dict[call_id, asyncio.Task]`; `def validate_spawn_batch(calls, known_task_ids, registry=None) -> SpawnBatchPlan` (pure, no I/O).
**Data Shape:** task_id = explicit arg or ToolCall.id; plan = `{task_id_by_call_id, depends_by_call_id, errors_by_call_id}`; completions recorded on the parent's own RunScope slot keyed by task_id (never inherited — children start fresh); every task resolves to AgentResult OR raises SpawnDependencyError — never any other shape.

### Decisive source
```python
# spawn_scheduler.py:188-198 — an invalid sibling can never record its
# task_id, so dependents would hang forever waiting: mark them invalid
# transitively, to a fixed point.
"""A call that depends on an already-invalid sibling can never actually
run ... mark it invalid too, transitively, to a fixed point."""
# :556-565 — the tight await-free launch loop is the concurrency contract:
"""Every task is created in this tight, await-free loop FIRST — so the
whole batch launches essentially simultaneously ... The observability
writes below used to be interleaved into THIS loop ... for a batch of N,
task N-1 could start up to N-1 checkpoint/timeline round-trips later."""
```

**Flow:** validate (duplicate/unknown/self/cyclic depends_on + unresolved tool names, each error actionable for the planner; cycle detection over in-batch edges only; transitive invalidity propagation) → create ALL tasks await-free (invalid ones as immediate raisers) → observability writes AFTER launch → dependent tasks wait `events[dep].wait()`, fail fast if a prerequisite failed, else fold each prerequisite's output into their goal (`_smart_truncate`: JSON-aware trailing-item drop at 24K chars) AND stage full un-truncated artifacts as sandbox input files under `input/artifacts/{task_id}/` → child runs via `build_spawn_child`/`run_spawned_child` → completion recorded to SPAWN_RESULTS_SLOT (works across turns; detached spawns record via `record_completed_spawn`) → caller awaits per-call; step's `finally` cancels still-running pre-launched tasks (no-op on completed ones).
**Invariant:** A prerequisite that fails SKIPS the dependent (never runs against missing data) and reports why; events always set in `finally` so waiters never hang; detach=true calls are excluded from the pre-launched batch (pre-launching them too caused a genuine double-spawn — see agent/__init__.py:849-859 comment).
**Probe:** `tests/unit/agent_loop_lib/agent/test_spawn_agent_dependencies.py::test_pdf_sub_agent_receives_jira_sub_agent_output` (:68), `::test_independent_spawns_still_run_without_extra_turns` (:121), `::test_failed_prerequisite_reports_actionable_error_to_planner` (:151); `tests/unit/agent_loop_lib/agent/test_spawn_orphans_on_step_failure.py::test_pre_launched_spawn_task_cancelled_when_dispatch_phase_raises` (:65), `::test_mixed_batch_only_cancels_still_running_tasks` (:155).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pipeshub-ai", query: "schedule_spawn_batch validate_spawn_batch SPAWN_RESULTS_SLOT depends_on", limit: 10, fields: ["signature", "name", "file"] });
await mcp.codebase_memory.trace_path({ project: "pipeshub-ai", function_name: "pipeshub-ai.backend.python.app.agent_loop_lib.agent.spawn_scheduler.schedule_spawn_batch", direction: "inbound" });
```

## Verdict
Adopt pure-validation→await-free-launch→per-call-await→finally-cancel, the cross-turn SPAWN_RESULTS_SLOT, JSON-aware truncation, and artifact file staging for full-fidelity handoff; adapt the char cap, slot key, and artifact path layout to host; omit team_id/E2B staging specifics unless you have sandboxes. Direct tests cover dependency folding, failure skipping, orphan cancellation, and mixed batches.
