<!-- capsule-v2 -->
# Per-agent tool concurrency guard — how do you stop parallel tool calls from racing shared state without a queue?

**Source:** agency-swarm MIT `main@4d1c35a6dd5ef038a5d15b39803459ff0b5f5578`; Codebase Memory `ext-agency-swarm`. **Question:** How does the framework enforce "one-call-at-a-time" and global tool serialization per agent, and what does the porter get wrong if they wrap only some tools?

## Wrap-on-add in-place guard over an inert counter object
**Path/Symbol:** `src/agency_swarm/agent/tools.py:_attach_one_call_guard` (:236-295) + `src/agency_swarm/tools/concurrency.py:ToolConcurrencyManager` (whole file, 63L).
**Signature:** `_attach_one_call_guard(tool: Tool, agent: Agent) -> None` (in-place, idempotent via `tool._one_call_guard_installed`); manager: `is_lock_active() -> tuple[bool, str | None]`, `acquire_lock(owner)`, `release_lock()`, `get_active_count()`, `increment_active_count()` / `decrement_active_count()` (floored at 0). Guard installed on EVERY add path incl. SendMessage registration in `src/agency_swarm/agent/subagents.py` :99 and :104.
**Data Shape:** `LockState(NamedTuple)` — immutable snapshot replaced wholesale (`self._lock_state = LockState(busy=True, owner=owner)`); opt-in flag is a tool ATTRIBUTE `one_call_at_a_time = True` (BaseTool.ToolConfig or function_tool attr), never a wrapper class.

### Decisive source
```python
# EVERY FunctionTool gets wrapped at add time; the guard reads the flag at INVOKE time
async def guarded_on_invoke(ctx, input_json: str):
    concurrency_manager = runtime_state.tool_concurrency_manager if runtime_state else agent.tool_concurrency_manager
    busy, owner = concurrency_manager.is_lock_active()
    if busy:                                   # ANY one_call tool running blocks EVERYTHING
        return f"Error: Tool concurrency violation. '{owner or 'unknown'}' tool is still running. ..."
    if one_call and concurrency_manager.get_active_count() > 0:
        return f"Error: ... Tool {tool.name} can only be used sequentially. ..."
    concurrency_manager.increment_active_count()
    if one_call:
        concurrency_manager.acquire_lock(getattr(tool, "name", "FunctionTool"))
    try:
        return await original_on_invoke(ctx, input_json)
    finally:
        if one_call: concurrency_manager.release_lock()
        concurrency_manager.decrement_active_count()
```

**Flow:** `add_tool()` → normalize → `_attach_one_call_guard(tool, agent)` for EVERY FunctionTool → guard closure captures agent but resolves the manager AT CALL TIME preferring `master_context.agent_runtime_state[agent.name].tool_concurrency_manager` (agency-shared instance) and falling back to the agent's own — so standalone and agency runs share one lock domain per logical agent.
**Invariant:** (1) The busy check precedes everything: while a one-call tool holds the lock, even NON-one-call tools are rejected — that is what makes "one-call" absolute rather than advisory; (2) rejection is an ERROR STRING returned to the model, not an exception — the LLM sees the violation and retries later; (3) active-count increments happen for all tools so the one_call check sees concurrent plain tools; (4) guards must be attached to tools added through EVERY path — constructor list, folder loading, schema parsing, MCP conversion, SendMessage registration (`_attach_one_call_guard(send_message_tool, agent)` in `agent/subagents.py` :99/:104) — wrapping only constructor tools leaves the backdoor open; (5) idempotence flag prevents double-wrap when the same tool object is re-added.
**Probe:** `tests/test_tools_modules/test_tool_system.py` :394 `test_base_tool_one_call_at_a_time_config`, :424 `test_base_tool_one_call_propagation`, :447 `test_base_tool_normal_tool_no_one_call`, :465 `test_agent_has_concurrency_manager`, :478 `test_agent_concurrency_manager_independence`. pytest runner-blocked this window; the stdlib-only manager contract was EXECUTED live at the pin (inert initial state, acquire→(True,owner), wholesale NamedTuple snapshot replacement on release, floored-at-0 decrement) — all green.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-agency-swarm", query: "ToolConcurrencyManager acquire_lock", limit: 10 });
// live-verified rank-1 line-exact 2026-08-24 (8 hits, all concurrency.py :26-63)
```

## Verdict
Adopt the two-tier guard (global busy latch + sequential-only flag) and errors-as-results rejection; adapt where the manager lives (runtime-state map keyed by logical agent name) to your context plumbing; omit the NamedTuple snapshot style if you need cross-thread atomicity — this primitive assumes single-event-loop execution. Probes green at HEAD.
