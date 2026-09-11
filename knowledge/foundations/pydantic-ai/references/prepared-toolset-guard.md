<!-- capsule-v2 -->
# PreparedToolset — prepare-function tool rewriting with add/rename guards

**Source:** pydantic-ai (MIT) `main@b3cdbc96796f0294f1ac6943cdba70d14af8a0ef`; Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai`. **Question:** When a porter lets a prepare function rewrite tool definitions per-run, what must be preserved and what must be forbidden (adding/renaming) so the tool-name contract stays stable?

## PreparedToolset prepare_func contract
**Path/Symbol:** `pydantic_ai/toolsets/prepared.py:PreparedToolset` (14-41).
**Signature:** `PreparedToolset(wrapped, prepare_func: ToolsPrepareFunc)` where `prepare_func(ctx, tool_defs: list[ToolDefinition]) -> list[ToolDefinition]` (sync or async); `get_tools(ctx)`.
**Data Shape:** `prepare_func` receives the ORIGINAL tool_defs (in order) and returns rewritten defs. Result is validated by `_utils.check_tools_prepare_func_result`.

### Decisive source
```python
async def get_tools(self, ctx):
    original_tools = await super().get_tools(ctx)
    original_tool_defs = [tool.tool_def for tool in original_tools.values()]
    result = self.prepare_func(ctx, original_tool_defs)
    if inspect.isawaitable(result):
        result = await result
    prepared_tool_defs_by_name = {
        tool_def.name: tool_def
        for tool_def in _utils.check_tools_prepare_func_result(result, self.prepare_func)
    }
    if len(prepared_tool_defs_by_name.keys() - original_tools.keys()) > 0:
        raise UserError(
            'Prepare function cannot add or rename tools. '
            'Use `FunctionToolset.add_function()` or `RenamedToolset` instead.')
    return {name: replace(original_tools[name], tool_def=tool_def)
            for name, tool_def in prepared_tool_defs_by_name.items()}
```

**Flow:** `get_tools` collects the original tool_defs, calls `prepare_func` (awaiting if async), validates the result, then rebuilds each `ToolsetTool` with its rewritten `tool_def` (preserving the original `ToolsetTool` shell — retries, validators, toolset identity). If the prepare function introduces any name not in the original set (i.e. it added or renamed a tool), it raises `UserError`.
**Invariant:** A prepare function may rewrite definitions in place but may NOT add or rename tools — the name set is fixed (adding/renaming is `FunctionToolset.add_function`/`RenamedToolset`'s job). The `ToolsetTool` shell (max_retries, args_validator, toolset) survives; only `tool_def` is swapped.
**Probe:** `tests/test_toolsets.py:test_prepared_toolset_sync_prepare_func` (302), `test_prepared_toolset_user_error_add_new_tools` (338), `test_prepared_toolset_user_error_change_tool_names` (373) — adding or renaming in the prepare func raises `UserError`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pydantic-ai", query: "PreparedToolset prepare_func cannot add or rename", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the rewrite-in-place / no-add-no-rename invariant and the shell-preserving `replace(original_tools[name], tool_def=...)`; adapt the error wording; omit nothing — the name-set-stability guard is the portable contract. Coverage clean.
