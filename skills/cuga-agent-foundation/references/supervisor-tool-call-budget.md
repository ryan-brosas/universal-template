<!-- capsule-v2 -->
# Supervisor tool-call budget — namespace-site enforcement with seed-and-persist across every exit

**Source:** cuga-agent Apache-2.0 `main@5de53ade`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** Your per-run tool-call cap was built inside ONE graph's sandbox, but a second graph (supervisor) executes its own generated code with its own tool context — how do delegation/skill/runtime/provider tools get capped without wrapping every registration site, and how do spent counts survive LangGraph's absent-key-keeps-checkpoint semantics?

## The budget contract
**Path/Symbol:** `src/cuga/backend/cuga_graph/nodes/cuga_supervisor/nodes/execute_agent_tool.py` (`_budget_updates` :45-56, `seed_call_budget` :90-93); `cuga_lite/tracking/tracker.py` (`ToolCallTracker`, `counted_tool_call`, `_tool_call_budget_context` contextvar); state fields `tool_calls_used_run` / `tool_calls_used_thread: Annotated[int, keep_highest]` (`agent_state.py:976`).
**Signature:** `_budget_updates() -> {tool_calls_used_run, tool_calls_used_thread, tool_budget_exhausted}`; `ToolCallTracker.seed_call_budget(run_used, thread_used)`; cap from `advanced_features.max_tool_calls_per_run` (default 256).
**Data Shape:** two counters — per-RUN (reset to 0 by the prepare node each turn) and per-THREAD (conversation ceiling carried via a monotonic reducer).

### Decisive source
```python
# execute_agent_tool.py:45-51 — WHY every exit must carry the counters
# Tool-call budget fields every exit from the execute node must carry.
# Each path runs *after* the delegation code, so each can be leaving spent
# budget behind. Omitting them leaves the keys absent from the update and the
# checkpoint keeps its pre-execution values, under-counting the ceiling.

# :87-89 — enforcement lives where generated code gets its NAMESPACE
# Tool-call budgets: carry the turn count from earlier steps and the
# conversation count from earlier turns. Without this the supervisor's
# delegation tools escape the caps entirely.
ToolCallTracker.seed_call_budget(
    getattr(state, "tool_calls_used_run", 0),
    getattr(state, "tool_calls_used_thread", 0),
)

# agent_state.py:30-40 — builtin max can't be a LangGraph reducer (no signature)
def keep_highest(current: Optional[int], incoming: Optional[int]) -> int:
    """...Monotonicity is what makes the conversation ceiling hold regardless of caller:
    the server rebuilds state from the checkpoint on every turn, so the incoming
    value is sometimes the field's default 0, which would otherwise silently reset
    the ceiling mid-conversation."""
    return max(current or 0, incoming or 0)
```

**Flow:** execute node seeds the tracker contextvar from state BEFORE running generated code → the tracker wraps ONLY coroutine-function entries of the injected namespace at eval time (plain callables = variables from earlier blocks, never charged) → every exit path (error command, step-limit Command, normal dict) spreads `**_budget_updates()` so spent counts always land in the update → prepare node resets `tool_calls_used_run=0` but deliberately NOT the thread counter → call_model reads `tool_budget_exhausted` and ends the turn with one final synthesis pass. The supervisor reuses the CugaLite tracker unchanged.
**Invariant:** enforce at the namespace boundary, not per-registration — that is what makes the cap hold for "tool kinds nobody thought to wrap" (test-stated property that must survive refactors). Absent key ≠ zero in LangGraph: an exit that omits the counters leaves stale checkpoint values, silently un-capping the conversation. The thread counter is monotonic via a hand-written reducer because rebuilt-state defaults would reset a naive counter mid-conversation.

**Probe:** direct tests `tests/test_supervisor_tool_call_cap.py`: `::test_supervisor_executor_seeds_the_budget` (:82-109, 20-loop vs cap 3), `::test_supervisor_budget_carries_across_steps` (:113-135), `::test_unwrapped_tool_is_still_capped` (:139-166, bare registration still charged), `::test_variables_are_not_charged_as_tool_calls` (:169-195), `::test_default_cap_is_256` (:198-210, settings.toml ↔ in-code fallback parity), `::test_supervisor_persists_the_thread_counter_and_exhausted_flag` (:214-241), `::test_step_limit_exit_still_persists_the_spent_budget` (:280-321).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "seed_call_budget _budget_updates keep_highest counted_tool_call tool_budget_exhausted", limit: 10 });
```

## Verdict
Adopt namespace-site budget enforcement + seed-before-exec/persist-on-every-exit as THE pattern for capping generated-code tool use across multiple graphs sharing one tracker; adopt the custom monotonic reducer for any cross-turn counter in checkpointed state. Adapt counter names and the exhausted-flag synthesis behavior to your host. Omit nothing.
