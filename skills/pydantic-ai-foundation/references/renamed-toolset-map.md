<!-- capsule-v2 -->
# RenamedToolset — bidirectional rename map with collision guards

**Source:** pydantic-ai (MIT) `main@b3cdbc96796f0294f1ac6943cdba70d14af8a0ef`; Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai`. **Question:** When a porter renames tools via a `{new: old}` map, how does the wrapper avoid silent drops on collision and correctly reverse the rename at call time?

## RenamedToolset map inversion + collision
**Path/Symbol:** `pydantic_ai/toolsets/renamed.py:RenamedToolset` (12-49).
**Signature:** `RenamedToolset(wrapped, name_map: dict[str, str])` where `name_map` maps NEW name → ORIGINAL name; `get_tools(ctx)`; `call_tool(name, tool_args, ctx, tool)`.
**Data Shape:** `name_map = {new_name: original_name}`. `original_to_new_name_map = {v: k for k, v in name_map.items()}`.

### Decisive source
```python
async def get_tools(self, ctx):
    original_to_new_name_map = {v: k for k, v in self.name_map.items()}
    original_tools = await super().get_tools(ctx)
    tools = {}
    for original_name, tool in original_tools.items():
        new_name = original_to_new_name_map.get(original_name, None)
        final_name = new_name or original_name
        if final_name in tools:
            if final_name != original_name:
                raise UserError(f'Renaming tool {original_name!r} to {final_name!r} conflicts with existing tool.')
            else:
                raise UserError(f'Tool name conflicts with previously renamed tool: {final_name!r}.')
        if new_name:
            tools[new_name] = replace(tool, toolset=self, tool_def=replace(tool.tool_def, name=new_name))
        else:
            tools[original_name] = tool
    return tools

async def call_tool(self, name, tool_args, ctx, tool):
    original_name = self.name_map.get(name, name)
    ctx = replace(ctx, tool_name=original_name)
    tool = replace(tool, tool_def=replace(tool.tool_def, name=original_name))
    return await super().call_tool(original_name, tool_args, ctx, tool)
```

**Flow:** `get_tools` inverts the map to `{original: new}`, then for each original tool: if renamed, emits under the new name with `toolset=self`; if not in the map, emits under its original name unchanged. Any name already taken raises `UserError` (both directions — a renamed tool landing on an existing name, or a renamed name already claimed). `call_tool` reverses via `name_map.get(name, name)` and rewrites `ctx.tool_name` + tool_def name back to the original before delegating.
**Invariant:** Renaming never silently drops a tool — a collision raises. A genuine swap (`{'b':'a','a':'b'}`) is NOT a collision and preserves both. Unmapped tools pass through untouched. `ctx.tool_name` is restored to the original at call time.
**Probe:** `tests/test_toolsets.py:test_renamed_toolset_name_collision` (1696) — renaming `a`→`b` raises `"Tool name conflicts with previously renamed tool: 'b'."`; renaming `b`→`a` raises `"Renaming tool 'b' to 'a' conflicts with existing tool."`; a genuine swap keeps both `['a','b']`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pydantic-ai", query: "RenamedToolset name_map collision", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the inverted-map + loud-collision + call-time-reverse pattern; adapt the error message wording; omit nothing — the silent-drop guard is the portable invariant. Coverage clean.
