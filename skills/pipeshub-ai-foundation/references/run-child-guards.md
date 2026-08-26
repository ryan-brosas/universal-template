<!-- capsule-v2 -->
# AgentRuntime.run_child — how does one launch a sub-agent with depth guards, tag stripping, and scope inheritance?

**Source:** pipeshub-ai (Apache-2.0) `main@4a02110dd9a7a644d8ba7a5ccd295c58a3c3628f`; Codebase Memory `pipeshub-ai`. **Question:** A porter building agent-to-agent composition (spawn_agent, best_of_n, agent_as_tool) must know the ONE place a child agent is launched and the invariants it enforces: spawn-depth guard, unconditional UI-only tool strip, depth-gated spawn-tool strip, parent-scope/run-context inheritance, and the streaming flag that makes a sub-agent's turns visible.

## The single child-launch choke point
**Path/Symbol:** `runtime/runtime.py:AgentRuntime.run_child` (118-247); `runtime/runtime.py:MAX_SPAWN_DEPTH` (37); `runtime/factory.py:AgentFactory.wire_sub_agents` (78-93).
**Signature:** `async run_child(spec: AgentSpec, goal: Goal, parent_run_ctx: RunContext | None, *, team_id=None, session_id=None, parent_scope: RunScope | None = None, mirror_events: bool = True) -> AgentResult`.
**Data Shape:** Used by both `agent_as_tool()`'s static composition and `spawn_agent`/`best_of_n`'s dynamic fan-out. `MAX_SPAWN_DEPTH = 3`. `session_id` carries the parent's session identity onto the child (session-scoped middleware/stores treat a spawn tree as one session). `parent_scope` is stashed on the child and consumed once at `run()` start to copy `inherit=True` `StateSlot` values down. `mirror_events=False` silences a child's token-level deltas on the parent's stream (for silent judge/critique sub-agents).

### Decisive source
```python
current_depth = getattr(parent_run_ctx, "spawn_depth", 0)
if current_depth >= MAX_SPAWN_DEPTH:
    raise AgentError(f"Maximum spawn depth ({MAX_SPAWN_DEPTH}) reached ...")

# EVERY child, at ANY depth, loses every TAG_UI_ONLY tool unconditionally —
# a UI-only tool talks to the human watching the ROOT run's stream; a spawned
# child has no such audience, so granting one lets the model stall the whole
# tree waiting on a question nobody will answer.
if self.tool_registry is not None and spec.tool_names:
    filtered = [t for t in spec.tool_names if TAG_UI_ONLY not in self.tool_registry.tags_for_name(t)]
    if len(filtered) != len(spec.tool_names):
        spec = spec.model_copy(update={"tool_names": filtered})

if current_depth >= MAX_SPAWN_DEPTH - 1:
    # One hop from the limit: strip TAG_SPAWN tools so the child can't spawn
    # further sub-agents — dispatched on the tag, not literal names, so a new
    # spawn-like tool is covered automatically.
    spec = spec.model_copy(update={"tool_names": [
        t for t in spec.tool_names if TAG_SPAWN not in registry.tags_for_name(t)]})

child = Agent(spec, self, session_id=session_id)
child.seed_context(ContextManager())
if parent_run_ctx is not None:
    child._run_ctx = parent_run_ctx.child(role_name=spec.name, model=spec.model.model, team_id=team_id)
elif team_id is not None:
    child._run_ctx.team_id = team_id
child._parent_scope = parent_scope
child.streaming = mirror_events  # else step() takes the non-streaming complete() branch
with maybe_start_agent_span(enabled=self.opik_enabled, role_name=spec.name, goal=goal, project_name=self.opik_project_name) as span:
    result = await child.run(goal)
    record_agent_span_result(span, result=result)
    return result
```

**Flow:** Depth guard first (raise before any span opens). Then strip `TAG_UI_ONLY` tools at every depth (category error, not a resource limit). Then, one hop from the limit, strip `TAG_SPAWN` tools (hard constraint, tag-dispatched). Build the child `Agent` on the shared runtime, seed a fresh `ContextManager`, inherit run context via `parent_run_ctx.child()` (propagates trace_id/team_id, sets `parent_run_id`), stash `parent_scope`, flip `child.streaming = mirror_events` so `step()` emits streaming deltas through the shared `event_emitter`, then run under an Opik `agent.{role_name}` span.
**Invariant:** `run_child` is the only child-launch path, so its guards apply uniformly to static composition AND dynamic fan-out. A child at any depth must never receive a UI-only tool. One hop from the limit must strip spawn tools regardless of how `spec.tool_names` was built. The child's `_streaming` flag must be True (unless `mirror_events=False`) or its turns silently take the non-streaming `complete()` branch and never emit transcript deltas. `AgentTool` static composition deliberately passes `parent_run_ctx=None` → children start with a clean scope/context.

**Probe:** `tests/unit/agent_loop_lib/runtime/test_run_child_streaming.py` (pins child flipped to `_streaming=True` before run; seeds context via public seam; inherits trace_id/parent_run_id). `tests/unit/agent_loop_lib/runtime/test_runtime_opik.py` (pins max-spawn-depth enforced BEFORE opening a span; no-parent-ctx still opens span but no run-context inheritance; Opik failure doesn't break child). `tests/unit/agent_loop_lib/agent/test_spawn_agent_detach.py` (real `run_child` launches exactly one child; records failure for later dependents).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pipeshub-ai", query: "run_child", limit: 10, fields: ["signature", "name", "file"] });
await mcp.codebase_memory.search_graph({ project: "pipeshub-ai", query: "MAX_SPAWN_DEPTH", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the single-child-launch choke point with its three guards (depth raise, unconditional UI-only strip, depth-gated spawn-tool strip by tag), the `parent_run_ctx.child()` inheritance (trace_id/team_id/parent_run_id), `parent_scope` one-shot stash for `inherit=True` StateSlots, `session_id` propagation for session-scoped middleware, and the `streaming=mirror_events` flip. Adopt `MAX_SPAWN_DEPTH=3` as a configurable ceiling. Adapt the tag names (`TAG_UI_ONLY`/`TAG_SPAWN`) and Opik span wiring to host. Omit the concrete `Agent`/`ContextManager` internals — the contract is the guard + inheritance ladder. Direct tests confirm all invariants; index coverage `no_recorded_issue`+`metadata_match` (best-effort caveat).
