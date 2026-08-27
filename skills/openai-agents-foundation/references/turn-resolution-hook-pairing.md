<!-- capsule-v2 -->
# Turn-resolution hook pairing — when do run-level and agent-level end/handoff hooks fire, and how are they paired?

**Source:** OpenAI Agents Python MIT `main@fe45b415`; Codebase Memory `openai-agents-python`. **Question:** At turn resolution, how are the run-level `RunHooks` and the per-agent `AgentHooks` paired for final output vs handoff — which events fire concurrently, which argument shapes each layer gets, and how many times does end-of-run fire across a multi-agent run?

## Concurrent run-level ∥ agent-level pairs; on_agent_end exactly once per run
**Path/Symbol:** `src/agents/run_internal/turn_resolution.py:` `_maybe_finalize_from_tool_results` (:216–258), `run_final_output_hooks` (:335–355), `execute_final_output_step` (:356–391), `execute_final_output` (:393–424), `execute_handoffs` (:527–680, on_handoff pair at :613–628); synthesized-output call sites `src/agents/run_internal/run_loop.py` :758 (`finalize_max_turns_handler_output`) and :1593 (max-turns handler result path).
**Signature:** `run_final_output_hooks(agent, hooks, context_wrapper, final_output) -> None`; `execute_handoffs(*, public_agent, ..., run_handoffs, hooks, context_wrapper, run_config, ...) -> SingleStepResult`.
**Data Shape:** two hook layers with DIFFERENT argument shapes — run-level `hooks.on_agent_end(agent_hook_context, agent, final_output)` / `hooks.on_handoff(context=..., from_agent=..., to_agent=...)` vs agent-level `agent.hooks.on_end(agent_hook_context, agent, final_output)` / `public_agent.hooks.on_handoff(context_wrapper, agent=new_agent, source=public_agent)`; the end pair shares an `AgentHookContext` built from context/usage/turn_input plus tool state shared via `context_wrapper._share_tool_state_with(...)`.

### Decisive source
```python
# run_final_output_hooks — one concurrent pair, first child exception wins
await gather_with_cancel(
    hooks.on_agent_end(agent_hook_context, agent, final_output),
    agent.hooks.on_end(agent_hook_context, agent, final_output)
    if agent.hooks is not None
    else _coro.noop_coroutine(),
)

# execute_handoffs — handoff NEVER fires on_agent_end; output committed BEFORE the pair
new_step_items.append(handoff_output)
if handoff_output_committer is not None:
    _register_tool_call_items(context_wrapper, [handoff_output])
    handoff_output_committer(handoff_output, new_agent)
await gather_with_cancel(
    hooks.on_handoff(context=context_wrapper, from_agent=public_agent, to_agent=new_agent),
    (public_agent.hooks.on_handoff(context_wrapper, agent=new_agent, source=public_agent)
     if public_agent.hooks is not None else _coro.noop_coroutine()),
)
```

**Flow:** final-output path: `_maybe_finalize_from_tool_results` (or the message path) → `execute_final_output_step` runs `run_final_output_hooks` BEFORE building the `SingleStepResult(NextStepFinalOutput)` — so both end hooks observe the validated final output and any hook exception aborts before the step result exists; the same function is called for SYNTHESIZED max-turns handler outputs at both run_loop sites, so a handler-recovered run still fires the end pair → handoff path: `execute_handoffs` resolves the target via `handoff.on_invoke_handoff`, appends the `HandoffOutputItem` to `new_step_items` and commits it through the committer, THEN fires the concurrent on_handoff pair; multiple handoff calls in one turn: only `run_handoffs[0]` executes — the rest get `ToolCallOutputItem("Multiple handoffs detected, ignoring this one.")` and a span error listing all requested agents → after either path, input filtering/history nesting for the next agent happens only after the hook pair settles.
**Invariant:** `on_agent_end` fires EXACTLY ONCE per run regardless of handoff count (handoffs never end the run); each lifecycle event pairs its run-level and agent-level hook in ONE `gather_with_cancel` (concurrent, first child exception wins, sibling cancelled+drained); the handoff output item is committed to step items BEFORE the on_handoff pair runs, so hooks observe an already-recorded transfer.
**Probe:** `tests/test_global_hooks.py::test_non_streamed_agent_hooks` (:76 — across tool turns + 2 handoffs + handoff-back: `on_agent_start` 3 (per agent segment), `on_handoff` 2, `on_agent_end` 1 "Should always have one end"), `tests/test_run_hooks.py::test_run_hooks_count_tool_and_handoff_invocations` (:329 — per-event counts incl. handoff invocation tracking).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "openai-agents-python", file_pattern: "turn_resolution.py", query: "on_agent_end on_handoff gather_with_cancel", limit: 20 });
await mcp.codebase_memory.trace_path({ project: "openai-agents-python", qualified_name: "openai-agents-python.src.agents.run_internal.turn_resolution.run_final_output_hooks", direction: "inbound" });
```

## Verdict
Adopt the concurrent run-level ∥ agent-level hook pair per lifecycle event (one gather-with-cancel, noop coroutine when the agent layer is unset) and the once-per-run end-of-run semantics for any multi-agent loop with per-agent customization points. Adapt the two-layer argument shapes to your host's hook API. Omit the synthesized-output call sites if you have no terminal-error recovery handlers that produce final outputs. Coverage: direct source+test reading fallback this pass (Codebase Memory MCP not connected); cited ranges read from checkout at fe45b415.
