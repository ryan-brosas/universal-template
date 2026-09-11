<!-- capsule-v2 -->
# ToolVisibility four-state resolution — how does a tool's name map to what the provider actually receives?

**Source:** pydantic-ai MIT `main@b3cdbc96796f0294f1ac6943cdba70d14af8a0ef`; Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai`. **Question:** What are the possible wire representations of a function tool on a request, and which derived views (declared tools, visibility lookup) must respect all of them?

## ToolVisibility + ModelRequestParameters derived views (`models/__init__.py`)
**Path/Symbol:** `pydantic_ai_slim/pydantic_ai/models/__init__.py:ToolVisibility = Literal['visible','deferred','withheld','via_history']` (:161-171), `ModelRequestParameters.visibility_of` (:240-251), `tool_defs`/`declared_tool_defs`/`declared_function_tools` cached properties (:253-272), `with_default_output_mode` (:280-289).
**Signature:** `visibility_of(tool_name: str) -> ToolVisibility`; `declared_function_tools -> list[ToolDefinition]`.
**Data Shape:** `tool_visibility: dict[str, ToolVisibility] | None` — `None` ONLY on authored parameters; `Model.prepare_request` stamps an entry for every function tool (empty dict = resolved-and-empty). Output tools never get entries.

### Decisive source
```python
# models/__init__.py:240-255 — lookup with an O(1) authored-parameters fallback
def visibility_of(self, tool_name):
    if visibility := (self.tool_visibility or {}).get(tool_name):
        return visibility
    # `tool_defs` is a cached dict, so the fallback stays O(1) — adapters call this in per-tool loops.
    tool_def = self.tool_defs.get(tool_name)
    return 'withheld' if tool_def is not None and tool_def.defer_loading else 'visible'

# :267-272 — the "ordinary tools collection" view excludes withheld AND via_history;
# output tools bypass this filter entirely (they are always plain entries)
return [tool for tool in self.function_tools
        if self.visibility_of(tool.name) not in ('withheld', 'via_history')]
```

**Flow:** four wire states per tool name — `'visible'` ordinary entry with schema; `'deferred'` declared entry whose schema sits behind the provider's schema-deferral flag until revealed; `'withheld'` absent entirely; `'via_history'` absent from the collection, definition traveling instead on the provider's mid-conversation tool-addition channel. Resolution happens in `prepare_request`: the full `_resolve_request_tools` swap path when anything is native/deferred, otherwise every function tool stamped `'visible'`. Output-tool lookups default absent entries to `'visible'`.

**Invariant:** Authored vs resolved is observable: `None` means unresolved, `{}` means resolved-and-empty — consumers must not treat them alike (the no-defaults repr hides resolved-only fields on authored parameters for exactly this reason). `declared_*` views must exclude BOTH absence states; only `visibility_of` collapses them back to defaults, and its fallback reads the CACHED dict because adapter per-tool loops make it a hot path.

**Probe:** `tests/test_tool_search.py::test_prepare_request_stamps_visibility_on_the_plain_path` (:7334 — pins None-vs-empty and the always-stamped invariant through real `prepare_request`); `tests/models/test_model_request_parameters.py::test_with_default_output_mode` family (:247-260).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pydantic-ai", query: "ToolVisibility visibility_of declared_function_tools tool_visibility", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the four-state taxonomy and the None-vs-empty authoring distinction; adopt the declared-view exclusion rule (both absence states) and the cached-dict O(1) fallback. Adapt state names to your transport. Omit nothing else. Coverage clean at the pinned commit.
