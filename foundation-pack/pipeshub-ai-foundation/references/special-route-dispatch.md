<!-- capsule-v2 -->
# Special-route registry + discovery fallback — how does a typed dispatch replace the string if/elif chain over agent-stateful tools?

**Source:** pipeshub-ai Apache-2.0 `main@4a02110dd9a7a644d8ba7a5ccd295c58a3c3628f`; Codebase Memory `pipeshub-ai`. **Question:** How do tools that need Agent-level state (todos, run_ctx, visible_tools) opt into custom dispatch WITHOUT bypassing the permission/middleware funnel?

## override_execute swap inside the normal funnel; discovery-based builtin fallback
**Path/Symbol:** `backend/python/app/agent_loop_lib/tools/special_route.py:RouteContext/SpecialRouteHandler/SpecialRouteRegistry/_builtin_fallback` (L43–191); consumption at `agent/tool_loop.py:321–355` (`override_execute` closure handed to `ToolExecutor.call_tool`).
**Signature:** `SpecialRouteRegistry(tool_registry).get(name) -> SpecialRouteHandler | None`; `async def handle(call, ctx: RouteContext) -> CoreToolResult`; `RouteContext(agent: AgentHandle, scope: ToolScope)` with read-through properties (`spec/goal/messages/todos/visible_tools/run_ctx/...`).
**Data Shape:** `scope.messages` is the FRESH post-response snapshot `ToolScope` carries (clarify's HIL checkpoint depends on exactly this — `TurnScope` deliberately has none).

### Decisive source
```python
# SpecialRouteRegistry.get — registered implementation ALWAYS wins:
if registry is not None and registry.has(name):
    tool = registry.resolve_by_name(name)
    if isinstance(tool, SpecialRouteHandler):
        return tool
return _builtin_fallback(name, registry)

# _builtin_fallback — DISCOVERY, not a hand-maintained name→class dict:
for cls in _BUILTIN_ROUTE_CLASSES:
    instance = cls()
    if instance.name == name:
        return instance
# dispatch goes by each tool's OWN `.name`, so renaming a builtin's name
# property (or adding a new special route) can never drift out of sync with
# a separate string key the way a literal {"spawn_agent": SpawnAgentTool,
# ...} mapping could. Instances are stateless → throwaway-per-lookup is safe;
# imports deferred to call time to break the circular import.

# tool_loop.py — the swap happens INSIDE call_tool, not around it:
handler = SpecialRouteRegistry(runtime.tool_registry).get(call.name)
async def override_execute():
    return await handler.handle(call, ctx)
tr = await agent._executor.call_tool(
    call, ..., override_execute=override_execute, ...)
# Pre/POST_TOOL_USE still wrap handle() — permission/approval/audit apply.
```

**Flow:** turn loop resolves handler for `call.name` → found ⇒ build `RouteContext(agent, tool_scope)` and pass `override_execute` → executor still runs resolve-before-authorize + PRE_TOOL_USE → `handle()` instead of `execute()` → POST_TOOL_USE as usual; not found ⇒ ordinary stateless execution.
**Invariant:** (1) Special routing swaps the EXECUTION HOOK ONLY — it must never skip authorization or middleware, which is why it rides `override_execute`. (2) Registry-first ordering means host overrides of builtin routes always win; the builtin fallback exists so runs without a wired registry still behave. (3) RouteContext duplicates no state: everything except genuine behavior (`emit`/`extract_text`) reads through `scope` — a narrower AgentHandle keeps handlers honest. (4) Discovery-over-dict makes rename/add drift impossible.
**Probe:** `tests/unit/agent_loop_lib/tools/test_special_route_agenthandle.py::test_special_route_reexports_the_same_protocol_object` (:15) pins Protocol identity across modules (the one direct test); behavioral pinning lives in the coordination/planning tool suites (spawn/best-of-n/clarify etc.) that drive this path end-to-end — caveat recorded.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pipeshub-ai", query: "SpecialRouteRegistry RouteContext _builtin_fallback override_execute", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the override-inside-funnel pattern + discovery-based fallback for any agent-stateful tool family; adapt the route class list to your builtins. Omit PipesHub's specific route set (already mined per-tool in earlier passes). One direct identity test; behavior otherwise pinned transitively via the route-tool suites — recorded honestly.
