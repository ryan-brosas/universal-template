<!-- capsule-v2 -->
# CombinedToolset — merging toolsets with name-conflict detection and source-tool routing

**Source:** pydantic-ai (MIT) `main@b3cdbc96796f0294f1ac6943cdba70d14af8a0ef`; Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai`. **Question:** When combining multiple toolsets into one, how does the framework flatten tools, detect name collisions, stamp toolset ids, and route a call back to the toolset that owns the tool?

## CombinedToolset flatten + conflict + routing
**Path/Symbol:** `pydantic_ai/toolsets/combined.py:CombinedToolset` (25-118), `_CombinedToolsetTool` (17-22).
**Signature:** `CombinedToolset(toolsets: Sequence[AbstractToolset])`; `get_tools(ctx) -> dict[str, ToolsetTool]`; `call_tool(name, tool_args, ctx, tool)`; `for_run/for_run_step` gather over children; `__aenter__` uses `AsyncExitStack`.
**Data Shape:** `_CombinedToolsetTool` wraps `{source_toolset, source_tool}` alongside the normal `ToolsetTool` fields. `id` property returns `None` (a combined toolset has no own id). `label` joins child labels.

### Decisive source
```python
async def get_tools(self, ctx):
    toolsets_tools = await gather(*(toolset.get_tools(ctx) for toolset in self.toolsets))
    all_tools = {}
    for toolset, tools in zip(self.toolsets, toolsets_tools):
        for name, tool in tools.items():
            tool_toolset = tool.toolset
            if existing_tool := all_tools.get(name):
                raise UserError(
                    f'{tool_toolset.label[0].upper() + tool_toolset.label[1:]} defines a tool '
                    f'whose name conflicts with existing tool from {existing_tool.toolset.label}: {name!r}. '
                    f'{toolset.tool_name_conflict_hint}')
            tool_def = tool.tool_def
            if tool_def.toolset_id is None and tool_toolset.id is not None:
                tool_def = replace(tool_def, toolset_id=tool_toolset.id)
            all_tools[name] = _CombinedToolsetTool(
                toolset=tool_toolset, tool_def=tool_def,
                max_retries=tool.max_retries, args_validator=tool.args_validator,
                args_validator_func=tool.args_validator_func,
                source_toolset=toolset, source_tool=tool)
    return all_tools

async def call_tool(self, name, tool_args, ctx, tool):
    assert isinstance(tool, _CombinedToolsetTool)
    return await tool.source_toolset.call_tool(name, tool_args, ctx, tool.source_tool)
```

**Flow:** `get_tools` gathers each child's tools concurrently, then iterates in child order. On a name collision it raises `UserError` (loud, not silent-drop). If a tool's `tool_def.toolset_id` is unset but its owning toolset has an `id`, it stamps the toolset id onto the tool_def (durable-execution identity). Each tool is wrapped in `_CombinedToolsetTool` recording which child toolset+tool produced it. `call_tool` routes back to `source_toolset.call_tool(..., source_tool)` — so execution reaches the true owner, not the combined container. `__aenter__` enters all children via `AsyncExitStack` and `pop_all()`s so one `aclose` closes all.
**Invariant:** Name collisions raise rather than silently overwrite (a silent drop would hide a tool from the model). `call_tool` must route to the source toolset, not execute locally. `for_run`/`for_run_step` propagate per-run copies to all children (gather), and return `self` only if every child returned the same instance.
**Probe:** `tests/test_toolsets.py:test_comprehensive_toolset_composition` (409) — composes prefixed→combined→filtered→prepared and asserts the final tool_defs snapshot; `test_combined_toolset_instructions` (1726) aggregates non-None child instructions; `test_combined_toolset_cancels_siblings_on_get_tools_failure` (1992).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pydantic-ai", query: "CombinedToolset get_tools conflict UserError", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the flatten-with-loud-conflict + source-tool routing pattern and the `AsyncExitStack`-based multi-enter lifecycle; adapt the `toolset_id` stamping to your durable-execution identity scheme (omit if you have none); the conflict error message format is host-specific prose but the raise-on-collision invariant is portable. Coverage clean.
