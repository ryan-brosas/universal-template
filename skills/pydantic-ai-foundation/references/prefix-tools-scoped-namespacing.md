<!-- capsule-v2 -->
# PrefixTools wrapper capability — namespace one wrapped capability's tools without touching the rest of the agent

## Source / Question
`pydantic_ai_slim/pydantic_ai/capabilities/prefix_tools.py` @ `main@b3cdbc96` (MIT); Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai`. **Question:** How do you prefix ONLY a wrapped capability's tool names (mcp_search instead of search) while leaving sibling tools unprefixed, including for callable toolsets that aren't AbstractToolsets? A porter will prefix globally or crash on ToolsetFunc callables.

## Path / Symbol
`capabilities/prefix_tools.py` — `PrefixTools(WrapperCapability)` dataclass (:15–67): `from_spec(prefix, capability)` nested-spec loading (:46–57), `get_toolset` override (:59–67).

## Signature
```python
def get_toolset(self) -> AgentToolset[AgentDepsT] | None:
    toolset = super().get_toolset()
    if toolset is None: return None
    if isinstance(toolset, AbstractToolset):
        return PrefixedToolset(toolset, prefix=self.prefix)
    return PrefixedToolset(DynamicToolset[AgentDepsT](toolset_func=toolset), prefix=self.prefix)
```

## Data Shape
Wraps another CAPABILITY (not a bare toolset) via `wrapped=Toolset(toolset_or_cap)`; nested `CapabilitySpec` loads through `load_capability_from_nested_spec`. Registration metadata (description/id/defer_loading) inherits from the wrapped capability unless explicitly overridden on PrefixTools.

### Decisive source
The two-branch wrap (:63–67): plain `AbstractToolset`s go straight under `PrefixedToolset`; ToolsetFunc callables are first materialized as `DynamicToolset(toolset_func=...)` because `PrefixedToolset` delegates by name mapping and needs an AbstractToolset interface. Call-time un-prefixing happens inside PrefixedToolset dispatch — the model calls `ns_greet`, the underlying `greet` executes.

**Flow:** `super().get_toolset()` yields the wrapped capability's contribution (None propagates — a prefix over nothing contributes nothing). Wrap → PrefixedToolset renames defs outward on listing AND strips the prefix on call dispatch. Deferred capabilities remain deferrable through the wrapper (deferral end-to-end preserved).

**Invariant:** Scoping — only the wrapped subtree's names change; the agent's other tools keep their identity. The prefix is applied at BOTH surfaces (listing and invocation) or not at all.

**Probe:** `tests/test_capabilities.py` — `test_apply_prefix_tools` (:5516), `test_prefix_tools_prefixes_wrapped_capability_tools` (:13122), `test_prefix_tools_with_callable_toolset` (:13197), `test_prefix_tools_returns_none_when_no_toolset` (:13191), `test_prefix_tools_inherits_wrapped_metadata_for_registration` (:13219), `test_prefix_tools_can_override_metadata` (:13248), `test_wrapper_over_deferred_capability_preserves_deferral_end_to_end` (:13303), `test_prefix_tools_tool_call_strips_prefix` (:13660 — ns_greet call reaches greet).

## Get live surrounding code
**Retrieve:**
```
search_graph --project mnt-hdd-utopia-inspo-pydantic-ai --query 'PrefixTools PrefixedToolset WrapperCapability get_toolset'
```

## Verdict
**Adopt** scoped-prefix-over-wrapped-capability semantics, the None passthrough, and the DynamicToolset materialization for callables. **Adopt** metadata inheritance-with-override for wrapper capabilities generally. **Omit** the nested-spec loader if you have no serializable capability specs.
