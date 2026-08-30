<!-- capsule-v2 -->
# Runner/handle Protocols + RunContext identity — what narrow surfaces do orchestrators and special routes depend on instead of the concrete Agent?

**Source:** pipeshub-ai Apache-2.0 `main@c28d133…`; Codebase Memory `mnt-hdd-utopia-inspo-platforms-pipeshub-ai`. **Question:** How do lower layers drive runs and emit events WITHOUT importing Agent (import cycles), and how does child identity inherit trace_id/team_id?

## AgentRunner/AgentHandle live in core/ because tools import them from BELOW agent/
**Path/Symbol:** `backend/python/app/agent_loop_lib/core/interfaces.py:AgentRunner/AgentHandle` (:23 / :59) + `core/context.py:RunContext/CancellationToken` (:9 / :45).
**Signature:** `AgentRunner.run(goal) -> AgentResult`; `.stream(goal, **run_kwargs) -> AsyncGenerator[AgentEvent, None]`; `.resume(checkpoint_id, hil_responses=None) -> AgentResult`; `.last_stream_result -> AgentResult | None`; `AgentHandle.extract_text(msg)` / `.emit(event_type, payload)`; `RunContext.child(role_name, model=None, team_id=None) -> RunContext`.
**Data Shape:** Both `@runtime_checkable` Protocols. `RunContext(run_id, agent_id, parent_run_id, trace_id, role_name, model, spawn_depth=0, team_id=None)` — trace_id shared across the whole agent tree, run_id unique per invocation, team_id marks genuinely CONCURRENT sibling batches (siblings of one parallel spawn batch share it so turn-memory writes retrieve team-scoped; None for solo/root). CancellationToken wraps an asyncio.Event.

### Decisive source
```python
"""Cross-cutting Protocols that don't belong to any single layer.
Lives in core/ (the one package every layer may import) rather than agent/,
since both AgentRunner and AgentHandle need to be referenced by code that
sits BELOW agent/ in the dependency graph (e.g. tools/special_route.py)
without creating an import cycle."""
...
    @property
    def last_stream_result(self) -> "AgentResult | None":
        """…stream() wraps run() in a background task (see agent/streaming.py)
        so the generator itself only yields AgentEvents, never the final
        result; callers that need BOTH the live event stream AND the terminal
        result (e.g. stream_bridge.py) read it off here once the generator
        is exhausted."""
```

**Flow:** Orchestration code/CLI/serve/tests type against `AgentRunner` instead of importing concrete `Agent` → special-route handlers receive `AgentHandle` (only `extract_text`/`emit` — genuine BEHAVIOR; spec/runtime/todos/visible_tools/run_ctx arrive via RouteContext.scope instead) → child contexts built via `child()` always increment spawn_depth and inherit trace_id (see run-child-guards for the launch path) → cancellation flows cooperatively: PRE_TURN guard observes token and raises RunCancelled.
**Invariant:** (1) These Protocols live in `core/` specifically so below-agent layers can import them — moving them back into `tools/` or `agent/` recreates the import cycle they exist to break (AgentHandle was historically in tools/special_route.py and moved; special_route still re-exports it). (2) `last_stream_result` is the ONLY sanctioned way to obtain a stream()'s terminal result — the generator yields events, never the result. (3) team_id means CONCURRENT sibling group only; stamping it on sequential spawns corrupts team-scoped memory retrieval.
**Probe:** No dedicated unit file for core/interfaces.py at this pin; runtime-checkable contracts are exercised by every agent test (duck-typed runners) — deterministic self-check: assert `isinstance(fake_with_run_stream_resume_only, AgentRunner)` fails until `last_stream_result` exists. RunContext identity pinned via `tests/unit/agent_loop_lib/runtime/test_run_child_streaming.py`.
**Retrieve:**
```bash
codebase-memory-mcp cli search_graph '{"project":"mnt-hdd-utopia-inspo-platforms-pipeshub-ai","query":"AgentRunner AgentHandle RunContext CancellationToken last_stream_result","detail":"ids","limit":5}'
```

## Verdict
Adopt the core/-placement rule for cross-layer Protocols, the handle-vs-scope split (behavior on the handle, state on RouteContext.scope), and the stream-yields-events/result-read-separately pairing. Adapt field sets on RunContext to your telemetry needs but keep trace_id-tree/run_id-per-invocation semantics. Omit nothing. Coverage caveat: interfaces.py has no dedicated suite; identity contracts ride runtime/streaming tests.
