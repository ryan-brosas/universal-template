<!-- capsule-v2 -->
# Byte-stable deferred-capability catalog instruction — why loaded entries must stay listed

## Source / Question
`pydantic_ai_slim/pydantic_ai/capabilities/_deferred_capability_loader.py` @ `main@b3cdbc96` (MIT); Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai`. **Question:** When deferred capabilities' tools stay hidden until the model calls `load_capability`, how do you render the "here is what you can load" catalog without destroying the prompt-cache prefix on every load? A porter will filter out already-loaded capabilities and bust the entire cached prefix at its very front each time anything loads.

## Path / Symbol
`capabilities/_deferred_capability_loader.py` — `DEFERRED_CAPABILITY_CATALOG_PREFIX` / `_PREFIX_WITH_SEARCH` constants (:20–27), `_resolve_capability_description` (str passthrough vs SystemPromptRunner over callable descriptions, :30–38), `_render_deferred_capability_catalog(ctx)` (:41–81, stability comment :42–57, two-signal search-surface detection :75–77), `DeferredCapabilityLoader` dataclass (:84–95): `get_instructions → _render_...`, `get_ordering → outermost, wrapped_by=[Instrumentation]`, `get_wrapper_toolset → DeferredCapabilityLoaderToolset`.

## Signature
```python
async def _render_deferred_capability_catalog(ctx: RunContext[AgentDepsT]) -> str
```
Registered as an instructions FUNCTION, so it renders into the request PREFIX ahead of message history.

## Data Shape
Catalog = `{cap_id: resolved_description}` for every capability with `defer_loading is True` in `ctx.capabilities`, rendered `- id: description` lines (bare `- id` when description resolves empty). Prefix variant chosen ONCE from authored signals, never mutated mid-run.

### Decisive source
The deliberate do-not-filter decision (:42–57):
```python
# Deliberately lists EVERY deferred capability on every turn, including ones the model
# has already loaded — do not filter by load state here.
# ... With static descriptions it renders byte-identical on every
# request, which keeps the provider's prompt-cache prefix warm across loads — the entire
# reason the native tool-search path exists. Dropping (or annotating) already-loaded
# capabilities would mutate that prefix the moment any capability load ...
# One occasional wasted retry is far cheaper than busting the prefix cache on every load.
```

**Flow:** Every request re-renders the full list (loaded ones included). The redundant-load case is handled where it belongs: the loader TOOLSET bounces an already-available load with a ModelRetry ("already available"). Search-surface steering: mention searching only when `TOOL_SEARCH_FUNCTION_TOOL_NAME in ctx.tools` OR any tool_def has `defer_loading and capability_id is None` (a searchable non-capability deferred tool marks the corpus for bm25/regex strategies); otherwise use the plain prefix — mentioning search in a run with none invites hallucinated search calls.

**Invariant:** Catalog bytes are identical across all turns of a run (multi-request property — single-request snapshots prove selection, not stability). Ordering position outermost but wrapped_by Instrumentation so spans still capture it.

**Probe:** `tests/test_capabilities.py` — `test_deferred_capability_catalog_bytes_stable_across_turns` (:2738 — run searches THEN loads then finishes, asserting identical instruction bytes throughout), `test_deferred_capability_catalog_mentions_search_only_when_search_surface_exists` (:2676), `test_abstract_capability_description_field_is_optional_in_deferred_catalog` (:2646).

## Get live surrounding code
**Retrieve:**
```
search_graph --project mnt-hdd-utopia-inspo-pydantic-ai --query 'DeferredCapabilityLoader catalog load_capability instructions'
```

## Verdict
**Adopt** byte-stable-by-construction dynamic instructions: never derive prompt-prefix text from mutable run state; handle state changes in tools (ModelRetry bounce), not prose. **Adopt** the two-signal surface detection before steering text mentions a capability. **Omit** the search-surface variant if your host has no tool-search corpus — the plain catalog still needs the no-filter rule.
