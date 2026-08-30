<!-- capsule-v2 -->
# PrefixedToolset — name-prefixing with call-time de-prefixing

**Source:** pydantic-ai (MIT) `main@b3cdbc96796f0294f1ac6943cdba70d14af8a0ef`; Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai`. **Question:** When a porter prefixes tool names to avoid cross-toolset collisions, how must the wrapper rewrite both the tool_def name AND the call-time name/ctx so the underlying tool receives its original name?

## PrefixedToolset prefix + de-prefix
**Path/Symbol:** `pydantic_ai/toolsets/prefixed.py:PrefixedToolset` (11-41).
**Signature:** `PrefixedToolset(wrapped, prefix: str)`; `get_tools(ctx)`; `call_tool(name, tool_args, ctx, tool)`.
**Data Shape:** new name = `f'{prefix}_{name}'`. `tool_name_conflict_hint` overridden to `'Change the prefix attribute...'`.

### Decisive source
```python
async def get_tools(self, ctx):
    return {
        new_name: replace(tool, toolset=self,
                          tool_def=replace(tool.tool_def, name=new_name))
        for name, tool in (await super().get_tools(ctx)).items()
        if (new_name := f'{self.prefix}_{name}')
    }

async def call_tool(self, name, tool_args, ctx, tool):
    original_name = name.removeprefix(self.prefix + '_')
    ctx = replace(ctx, tool_name=original_name)
    tool = replace(tool, tool_def=replace(tool.tool_def, name=original_name))
    return await super().call_tool(original_name, tool_args, ctx, tool)
```

**Flow:** `get_tools` rewrites each tool_def's `name` to `prefix_name` and rebinds `toolset=self` (so conflict hints and ownership point at the prefixing wrapper). `call_tool` strips the prefix back off, rewrites `ctx.tool_name` to the original, rewrites the tool_def name back, then delegates with the ORIGINAL name. The tool body and any `RunContext.tool_name`-based logic see the unprefixed name.
**Invariant:** The prefix is a wire-level alias only — the underlying tool, its `ctx.tool_name`, and the tool_def handed to the body must all be de-prefixed at call time, or tool functions that branch on `ctx.tool_name` break. The `if (new_name := ...)` walrus guard means a tool is always included (the assignment is always truthy).
**Probe:** `tests/test_toolsets.py:test_comprehensive_toolset_composition` (409) — prefixed toolsets (`math_`, `str_`, `adv_`) combined and filtered by prefix; the final tool_defs snapshot shows `math_add`, `str_concat` etc.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pydantic-ai", query: "PrefixedToolset prefix removeprefix", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the prefix-on-get / de-prefix-on-call symmetry (including rewriting `ctx.tool_name`); adapt the separator (`_`) to your host; omit nothing — the de-prefix of ctx.tool_name is the easy-to-miss invariant. Coverage clean.
