<!-- capsule-v2 -->
# CapabilityOwnedToolset — binding a contributed toolset to its owning capability

**Source:** pydantic-ai (MIT) `main@b3cdbc96796f0294f1ac6943cdba70d14af8a0ef`; Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai`. **Question:** When a capability contributes a toolset, how does the framework stamp each tool with the capability's id and defer_loading flag, and how does it decide whether a deferred-capability-gated tool is searchable?

## CapabilityOwnedToolset stamping + gating predicates
**Path/Symbol:** `pydantic_ai/toolsets/_capability_owned.py:CapabilityOwnedToolset` (17-49), `resolve_capability_id` (52-63), `is_gated_by_deferred_capability` (66-80), `tool_defs_from_pre_definition_load_returns` (83-95).
**Signature:** `CapabilityOwnedToolset(wrapped, capability)`; `get_tools(ctx)`; `get_instructions(ctx)`.

### Decisive source
```python
async def get_tools(self, ctx):
    tools = await self.wrapped.get_tools(ctx)
    capability_id = resolve_capability_id(ctx, self.capability)
    defer_loading = self.capability.defer_loading is True
    result = {}
    for name, tool in tools.items():
        tool_def = tool.tool_def
        result[name] = replace(tool, tool_def=replace(
            tool_def,
            capability_id=tool_def.capability_id if tool_def.capability_id is not None else capability_id,
            defer_loading=defer_loading or tool_def.defer_loading))
    return result

def resolve_capability_id(ctx, capability):
    for capability_id, registered_capability in ctx.capabilities.items():
        if registered_capability is capability:
            return capability_id
    raise RuntimeError('Capability ... is not registered in this run')

def is_gated_by_deferred_capability(ctx, tool_def):
    return ((capability_id := tool_def.capability_id) is not None
            and (cap := ctx.capabilities.get(capability_id)) is not None
            and cap.defer_loading is True)
```

**Flow:** `get_tools` resolves the capability's registry id (via `resolve_capability_id` — the id a capability was registered under in `ctx.capabilities`), then stamps each tool_def with `capability_id` (only if not already set) and ORs the capability's `defer_loading` onto the tool. `get_instructions` returns `None` when the capability defers loading (its instructions must not reach the prompt until loaded). `is_gated_by_deferred_capability` decides whether a deferred tool is a member of the searchable corpus: only if its owning capability defers loading — such a tool is hidden until the capability loads and is NEVER searchable (the model must not reach it by asking).
**Invariant:** A tool's `capability_id` defaults to its owning capability's resolved registry id (not overwriting an explicit one). `defer_loading` is the OR of capability and tool flags. A capability-gated deferred tool is hidden-and-unssearchable; an ungated deferred tool is hidden-but-searchable. `resolve_capability_id` raises if the capability isn't registered (internal error).
**Probe:** `tests/test_capabilities.py` covers capability-owned toolset stamping and deferred-capability gating (deferral-legality and load-gating tests).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pydantic-ai", query: "CapabilityOwnedToolset resolve_capability_id is_gated_by_deferred_capability", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the capability-id stamping (default-not-overwrite) and the OR'd defer_loading, plus the searchable-vs-hidden gating distinction; adapt `ctx.capabilities` registry shape to your host; omit nothing — the gated-tool-is-unssearchable rule is the portable invariant. Coverage clean.
