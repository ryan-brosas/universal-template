<!-- capsule-v2 -->
# FilteredToolset + metadata/defer/return-schema prepare wrappers — the PreparedToolset subclasses

**Source:** pydantic-ai (MIT) `main@b3cdbc96796f0294f1ac6943cdba70d14af8a0ef`; Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai`. **Question:** How do FilteredToolset, SetMetadataToolset, DeferredLoadingToolset, and IncludeReturnSchemasToolset each specialize the wrapper/prepare machinery, and what per-tool flag does each flip?

## The four small wrapper/prepare specializations
**Path/Symbol:** `pydantic_ai/toolsets/filtered.py:FilteredToolset` (13-32), `set_metadata.py:SetMetadataToolset` (12-28), `deferred_loading.py:DeferredLoadingToolset` (11-37), `include_return_schemas.py:IncludeReturnSchemasToolset` (11-26).
**Signature:** `FilteredToolset(wrapped, filter_func)` — sync/async `(ctx, tool_def) -> bool`; `SetMetadataToolset(wrapped, metadata: dict)`; `DeferredLoadingToolset(wrapped, *, tool_names: frozenset|None)`; `IncludeReturnSchemasToolset(wrapped)`.

### Decisive source
```python
# filtered.py — filter drops tools by predicate
async def get_tools(self, ctx):
    result = {}
    for name, tool in (await super().get_tools(ctx)).items():
        match = self.filter_func(ctx, tool.tool_def)
        if inspect.isawaitable(match):
            match = await match
        if match:
            result[name] = tool
    return result

# set_metadata.py — a PreparedToolset whose prepare_func merges metadata
async def _set_metadata(ctx, tool_defs):
    return [replace(td, metadata={**(td.metadata or {}), **self.metadata}) for td in tool_defs]

# deferred_loading.py — a PreparedToolset that flips defer_loading
async def _mark_deferred(_ctx, tool_defs):
    return [replace(td, defer_loading=True) if (tool_names is None or td.name in tool_names) else td
            for td in tool_defs]

# include_return_schemas.py — a PreparedToolset that sets include_return_schema
async def _include(ctx, tool_defs):
    return [replace(td, include_return_schema=True) if td.include_return_schema is None else td
            for td in tool_defs]
```

**Flow:** `FilteredToolset` overrides `get_tools` to keep only tools whose `filter_func(ctx, tool_def)` is truthy (awaiting async predicates). The other three are `PreparedToolset` subclasses that inject a prepare_func at construction: `SetMetadataToolset` merges `metadata` dicts (existing wins via `{**old, **new}` order — new overrides old); `DeferredLoadingToolset` sets `defer_loading=True` on all tools or only those in `tool_names`; `IncludeReturnSchemasToolset` sets `include_return_schema=True` only where it's currently `None` (does not override an explicit `False`).
**Invariant:** Filtering happens at `get_tools` (per-run, after prepare), so it sees the final tool_defs. The prepare-based wrappers all preserve the `ToolsetTool` shell and only rewrite `tool_def`. `DeferredLoadingToolset` with `tool_names=None` defers ALL tools; with a set, only those named. `IncludeReturnSchemasToolset` respects an explicit `include_return_schema=False` (only fills `None`).
**Probe:** `tests/test_toolsets.py:test_comprehensive_toolset_composition` (409) uses `FilteredToolset` + `PreparedToolset`; `test_function_toolset_instructions_none_filtered` (1901) exercises filtering.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pydantic-ai", query: "FilteredToolset SetMetadataToolset DeferredLoadingToolset", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the filter-at-get_tools and prepare-func-flag-flip patterns; adapt which tool_def flags your host carries (`defer_loading`, `include_return_schema`, `metadata`); omit the exact flag names if your tool model differs. Coverage clean.
