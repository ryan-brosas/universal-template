<!-- capsule-v2 -->
# get_wrapper_toolset — how capabilities stack wrappers around the agent's toolset

**Source:** pydantic-ai (MIT) `main@b3cdbc96796f0294f1ac6943cdba70d14af8a0ef`; Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai`. **Question:** When a porter lets capabilities wrap the agent's toolset (e.g. tool search, set-metadata), what is the stacking order and how does a combined capability fold the wrappers?

## get_wrapper_toolset stacking contract
**Path/Symbol:** `pydantic_ai/capabilities/combined.py:CombinedCapability.get_wrapper_toolset` (254-262); `abstract.py:AbstractCapability.get_wrapper_toolset` (415); `capabilities/wrapper.py:WrapperCapability.get_wrapper_toolset` (163-164); concrete overrides in `_tool_search.py` (179), `set_tool_metadata.py` (44), `include_return_schemas.py` (53), `_deferred_capability_loader.py` (94).
**Signature:** `get_wrapper_toolset(toolset) -> AbstractToolset | None` — returns a wrapped toolset or `None` (no wrapping).
**Data Shape:** `toolset` is the agent's combined toolset; each capability may return a new wrapped toolset.

### Decisive source
```python
def get_wrapper_toolset(self, toolset):
    wrapped = toolset
    any_wrapped = False
    for capability in reversed(self.capabilities):
        result = capability.get_wrapper_toolset(wrapped)
        if result is not None:
            wrapped = result
            any_wrapped = True
    return wrapped if any_wrapped else None
```

**Flow:** `CombinedCapability.get_wrapper_toolset` iterates capabilities in REVERSE, threading the accumulated `wrapped` toolset through each capability's `get_wrapper_toolset`. The LAST capability in `capabilities` wraps first (innermost), the FIRST wraps last (outermost) — matching the `wrap_*` middleware direction. A capability returning `None` is skipped. If nothing wrapped, returns `None`. The agent applies this in `agent/__init__.py:3061` (`toolset = run_capability.get_wrapper_toolset(toolset) or toolset`) around the prepare_tools wrap, so wrapper toolsets sit outside the prepare step.
**Invariant:** Wrapper stacking is reverse-order (last capability = innermost wrapper), consistent with all other `wrap_*` middleware. `None` means "no wrapper" and is distinct from an identity wrapper. The wrapper toolset is applied around (outside) the prepare_tools step.
**Probe:** `tests/test_capabilities.py` covers tool-search / set-metadata wrapper-toolset application around the agent toolset.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pydantic-ai", query: "get_wrapper_toolset reversed capabilities wrap", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the reverse-order folding and the `None`-means-no-wrapper contract; adapt which capabilities wrap to your host; omit nothing — the stacking order is the portable invariant. Coverage clean.
