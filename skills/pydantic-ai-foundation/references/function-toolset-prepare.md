<!-- capsule-v2 -->
# FunctionToolset.get_tools — per-tool prepare contexts, rename preservation, and the durable rebuild seam

**Source:** pydantic-ai (MIT) `main@b3cdbc96796f0294f1ac6943cdba70d14af8a0ef`; Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai`. **Question:** When a toolset turns stored `Tool` objects into per-step callable tools, what RunContext does each prepare see, how are prepare-renames kept consistent with the storage key, and how does durable execution rebuild tools without re-running prepares?

## FunctionToolset.get_tools / tool_for_tool_def
**Path/Symbol:** `pydantic_ai_slim/pydantic_ai/toolsets/function.py:FunctionToolset` (50-693), `get_tools` (608-632), `tool_for_tool_def` (634-661), `_tool_for` (663-676).
**Signature:** `async get_tools(ctx) -> dict[str, ToolsetTool]`; `tool_for_tool_def(tool_def, *, ctx, original_name=None) -> FunctionToolsetTool`.
**Data Shape:** `tools: dict[str, Tool]` keyed by ORIGINAL name; `FunctionToolsetTool` adds `call_func`, `is_async`, `timeout`, `original_name` on top of the ToolsetTool base.

### Decisive source
```python
for original_name, tool in self.tools.items():
    max_retries = tool.max_retries if ... else self.max_retries
    if max_retries is None: max_retries = ctx.max_retries     # 3-level ladder
    run_context = replace(ctx,
        tool_name=original_name,                              # the STORAGE key, not the def name
        retry=ctx.retries.get(original_name, 0),
        max_retries=max_retries)
    tool_def = await tool.prepare_tool_def(run_context)       # per-tool prepare; None => omit
    if not tool_def: continue
    new_name = tool_def.name
    if new_name in tools:
        if new_name != original_name:
            raise UserError(f'Renaming tool {original_name!r} to {new_name!r} conflicts...')
        else:
            raise UserError(f'Tool name conflicts with previously renamed tool: {new_name!r}.')
    tools[new_name] = self._tool_for(tool, tool_def, max_retries, original_name)

# durable-execution seam: rebuild from an ALREADY-prepared definition
def tool_for_tool_def(self, tool_def, *, ctx, original_name=None):
    original_name = original_name or tool_def.name   # equal only when no prepare renamed it
    tool = self.tools[original_name]
    ...
    return self._tool_for(tool, tool_def, max_retries, original_name)
```

**Flow:** for each stored tool → resolve retries (tool → toolset → ctx) → clone the RunContext with `tool_name=<storage key>`, that tool's current retry count and resolved budget → prepare the definition (prepare may rename or return None to omit) → collision-check against already-emitted names (rename-collision vs same-name-conflict get distinct errors) → emit under the NEW name while keeping `original_name` on the callable.
**Invariant:** Prepare sees the ORIGINAL storage-key name in `ctx.tool_name`, even though the tool is exposed under a possibly-renamed def — filtering logic keyed on names stays stable. Retry resolution is exactly three levels with no implicit default inside the toolset. The durable rebuild must NOT re-run prepare (different RunContext inside the activity); it re-keys by `original_name`.
**Probe:** `tests/test_toolsets.py::test_function_toolset_tool_for_tool_def_preserves_rename_and_retry_budget` (120) pins rename preservation + budget; rename-collision error pinned at 1696-1719.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pydantic-ai", query: "FunctionToolset get_tools tool_for_tool_def original_name prepare_tool_def", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the storage-key-vs-def-name split and the no-reprepare durable rebuild; adapt the retry ladder defaults to your host's config surface; omit the docstring/schema-generation options (host-specific schema derivation). Coverage clean.
