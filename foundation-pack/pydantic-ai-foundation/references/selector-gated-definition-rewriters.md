<!-- capsule-v2 -->
# Selector-gated definition rewriters — IncludeToolReturnSchemas and SetToolMetadata as PreparedToolset wrappers that respect per-tool opt-outs

## Source / Question
`pydantic_ai_slim/pydantic_ai/capabilities/include_return_schemas.py` + `capabilities/set_tool_metadata.py` @ `main@b3cdbc96` (MIT); Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai`. **Question:** How do you apply a cross-cutting flag/metadata to a SELECTABLE subset of tools via one capability without clobbering per-tool explicit configuration? A porter will overwrite tool-level opt-outs with the capability-level default.

## Path / Symbol
`include_return_schemas.py` — `IncludeToolReturnSchemas` (:16–67): `tools: ToolSelector = 'all'` (:40), `get_wrapper_toolset` with `td.include_return_schema is None` guard (:56–65). `set_tool_metadata.py` — `SetToolMetadata` dataclass(init=False) (:16–56): kwargs-style `__init__(*, tools='all', **metadata)` (:31–38), merge `{**(td.metadata or {}), **metadata}` (:52).

## Signature
```python
async def _include_return_schemas(ctx, tool_defs) -> list[ToolDefinition]:
    for td in tool_defs:
        # Only set the flag on tools that haven't explicitly opted in or out
        if td.include_return_schema is None and await matches_tool_selector(selector, ctx, td):
            td = replace(td, include_return_schema=True)
```

## Data Shape
ToolSelector union: `'all'` | `Sequence[str]` (names) | `dict[str, Any]` (deep metadata inclusion match) | async/sync predicate `(ctx, tool_def) -> bool`; resolved per-request through `matches_tool_selector` (awaited even for sync predicates). Both capabilities return `PreparedToolset(toolset, prepare_func)` from `get_wrapper_toolset`, so rewriting happens at every listing inside the normal prepare pipeline.

### Decisive source
The tri-state precedence: `None` means "unconfigured" — only then does the capability write its value; explicit `True`/`False` on the ToolDefinition always wins. Metadata twin uses MERGE not replace (`{**(td.metadata or {}), **metadata}` — capability keys win collisions but existing keys survive). Serialization names are set ('IncludeToolReturnSchemas'/'SetToolMetadata') because both are fully spec-constructible.

**Flow:** Listing time: for each def, selector match → conditional rewrite → append unchanged otherwise. Return-schema consumers split on model support: native return-schema providers (Gemini) get a structured field; others get JSON text injected into the description. Metadata is consumed downstream (e.g. code_mode) rather than by this layer.

**Invariant:** Capability-level configuration is a DEFAULT, never an override of explicit tool-level choices; rewrites are pure (`replace`) so shared definitions aren't mutated.

**Probe:** `tests/test_capabilities.py` — spec round-trips pin both serialization names (schema assertions ~:1700–1780 region); selector semantics pinned by tool-selector tests; coverage caveat: no dedicated e2e file isolates these two wrappers — behavior verified through PreparedToolset integration tests.

## Get live surrounding code
**Retrieve:**
```
search_graph --project mnt-hdd-utopia-inspo-pydantic-ai --query 'IncludeToolReturnSchemas SetToolMetadata matches_tool_selector'
```

## Verdict
**Adopt** tri-state default-vs-override discipline and pure `replace()` rewrites behind wrapper toolsets. **Adopt** the four-shape ToolSelector as your reusable selection vocabulary. **Omit** the return-schema description-injection path if your models all take structured fields.
