<!-- capsule-v2 -->
# run_spawned_child (single-AgentTool wrapper bypass)

## Source
pipeshub-ai Apache-2.0 `main@4a02110d`; Codebase Memory `pipeshub-ai`. **Question:** When a spawn's tool list resolves to exactly one AgentTool, why skip the generic ReAct wrapper — and when MUST the bypass not fire?

## Path/Symbol
`tools/builtin/coordination/spawn_agent.py` — `_single_agent_tool(runtime, spec)` (:78–102), `run_spawned_child(runtime, spec, goal, parent_run_ctx, **kwargs)` (:105–137). Test: `tests/unit/agent_loop_lib/agent/test_spawn_agent_direct_dispatch.py`.

## Signature
`_single_agent_tool` returns the AgentTool iff `registry.expand_tool_names(spec.tool_names)` yields EXACTLY one registered tool AND it's an `AgentTool` AND `tool.share_parent_results` is False; else None → normal `runtime.run_child(wrapper_spec, ...)`.

## Data Shape
Bypass path: `run_child(direct_tool.spec, goal, parent_run_ctx, **kwargs)` — the DOMAIN spec (its tuned max_turns/name/system prompt), not the wrapper; on success rewrites output via `result.model_copy(update={"output": direct_tool.finalize_output(result)})`.

### Decisive source
```python
result = await runtime.run_child(direct_tool.spec, goal, parent_run_ctx, **run_child_kwargs)
if result.success:
    # `finalize_output` (not the narrower `apply_result_note`) so a
    # `needs_input` escalation survives this bypass too — see
    # `AgentTool.finalize_output`'s docstring.
    result = result.model_copy(update={"output": direct_tool.finalize_output(result)})
```

**Flow:** parent spawns role whose tools = [one domain agent] → wrapper would do nothing but phrase ONE call to it and lossily RE-NARRATE its result as its own final answer (an extra LLM round-trip + fidelity loss — a condensing rewrite was OBSERVED at exactly that hop, which is why internal_exploration_agent needed a result_note at all) → dispatch straight to the domain spec instead, applying result_note as handle() would.

**Invariant:** The bypass is FORBIDDEN when `share_parent_results=True`: that behavior needs the CALLING agent's conversation (`ctx.messages`), which only `AgentTool.handle()`'s RouteContext has — bypassing silently drops the child's digest/staged file. finalize_output (not apply_result_note) because needs_input must survive as `[ESCALATION]`. Every non-matching shape runs unchanged through run_child.

**Probe:** `test_spawn_agent_direct_dispatch.py` — `test_single_agent_tool_skips_the_wrapper_hop` :94 (3 model calls vs 5; result_note applied without handle()), `test_share_parent_results_falls_back_to_wrapper` :128 (all 5 turns consumed).

## Get live surrounding code
**Retrieve:**
```bash
codebase-memory-mcp cli search_graph --project pipeshub-ai --semantic-query '["run_spawned_child","_single_agent_tool","share_parent_results"]'
```

## Verdict
Adopt single-tool delegation shortcut with its two guards (share_parent_results veto, finalize_output-not-apply_result_note); adapt registry expansion API.
