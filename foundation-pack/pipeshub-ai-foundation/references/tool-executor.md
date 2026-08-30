<!-- capsule-v2 -->
# ToolExecutor + name repair — how do you guarantee every tool call passes the same hook pipelines, and how do you recover degenerate tool names before failing?

**Source:** pipeshub-ai Apache-2.0 `main@4a02110d`; Codebase Memory `pipeshub-ai`. **Question:** What is the one funnel every tool call must pass through, and what does "resolve BEFORE authorize" buy you?

## resolve → PRE_TOOL_USE → execute → POST_TOOL_USE, exactly once
**Path/Symbol:** `backend/python/app/agent_loop_lib/tools/executor.py:ToolExecutor.call_tool` (135-248); `_resolve_tool_name` (250-282); `_collapse_repeated_name` (60-85); `_usage_hint` (88-104); `_run` (284-333).
**Signature:** `async def call_tool(call, *, session_id=None, caller="agent", override_execute=None, on_denied=None, on_ask=None, scope=None) -> CoreToolResult`.
**Data Shape:** `override_execute` replaces `Tool.execute()` for special routes (spawn_agent/best_of_n/clarify/replan/handoff) that need Agent-level state — but Pre/POST_TOOL_USE still wrap it, so permission/mode/approval/audit middleware apply uniformly. Resolution is mirrored onto the SAME `ToolScope` object handlers already hold (`scope.tool_path`/`.tags` filled post-resolution).

### Decisive source
```python
# executor.py:60-74 — models echo a hallucinated doubled name forever;
# collapsing often turns the call into one that resolves on first occurrence.
def _collapse_repeated_name(name: str) -> str | None:
    """Some models/gateways degenerate into echoing an already-hallucinated
    tool name doubled, then quadrupled... (observed: OpenAI's 128-char
    function-name cap) until the whole request is rejected outright."""
    for unit_len in range(1, length // 2 + 1):
        if length % unit_len: continue
        unit = name[:unit_len]
        if unit * (length // unit_len) == name:
            return unit
```
```python
# executor.py:265-282 — resolve FIRST so authorization sees the real tool
"""call_tool calls this BEFORE building ToolCallContext so PRE_TOOL_USE
authorizes against the resolved tool's real path/tags — resolving only in
_run ... would let allow/deny-list, risk-tag, and destructive-command-pattern
middleware apply to the wrong tool entirely."""
if self._registry.has(name): return name
collapsed = _collapse_repeated_name(name)
if collapsed and collapsed != name and self._registry.has(collapsed): return collapsed
candidates = self._registry.expand_tool_names([name])   # toolset group name
if len(candidates) == 1: return candidates[0]           # unambiguous → member
return name
```

**Flow:** resolve (exact → repeated-collapse → single-candidate group expansion) → build ToolCallContext with REAL path/tags → PRE_TOOL_USE dispatch → decision ALLOW passes / ASK consults `on_ask` (no HIL store ⇒ degrades to DENY) / deny ⇒ `on_denied(reason)` + error result → execute via override or registry (validation failure appends `_usage_hint`: the full parameter list so a weak model can fix the call in ONE turn instead of flailing to its 3-strike limit) → POST_TOOL_USE dispatch (BLOCK ⇒ error result; artifact_meta rides in post_ctx.metadata).
**Invariant:** No caller can bypass hooks by calling `Tool.execute()` directly — sandbox RPC bridge and turn loop both use call_tool. ASK without an on_ask callback = DENY. Ambiguous group names stay errors ("that's a toolset name, not a callable tool: <members>").
**Probe:** `tests/unit/agent_loop_lib/tools/test_executor_repeated_name_repair.py::test_doubled_valid_name_resolves_to_base_tool` (:58), `::test_repeated_but_unregistered_base_still_errors` (:79), `::test_doubled_name_authorizes_against_resolved_path_and_tags` (:117), `::test_unresolvable_name_still_authorizes_against_unresolved_placeholder` (:150).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pipeshub-ai", query: "ToolExecutor call_tool _resolve_tool_name collapse repeated", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the single call_tool funnel with override_execute for agent-stateful routes, resolve-before-authorize ordering, repeated-name collapse, and usage-hint validation errors; adapt the tag/middleware set and HIL wiring to host; omit Opik span bridging. Direct tests cover all four repair/error branches plus authorization-vs-resolved-path coupling.
