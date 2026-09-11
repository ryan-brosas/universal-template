<!-- capsule-v2 -->
# Native-tool swap resolution — the per-tool decision table that turns native tools, local fallbacks, and deferred loading into one wire shape

**Source:** pydantic-ai MIT `main@b3cdbc96796f0294f1ac6943cdba70d14af8a0ef`; Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai`. **Question:** Given a request carrying native tools, function tools with `unless_native`/`with_native`/`defer_loading`, how does each tool resolve to visible/deferred/withheld on THIS model?

## `resolve_request_tools`
**Path/Symbol:** `pydantic_ai_slim/pydantic_ai/models/__init__.py:resolve_request_tools` (:1744–1868); called from `Model._resolve_request_tools` (:831–838) and directly from the realtime path (RealtimeModel is not a Model subclass — hence module-level).
**Signature:** `resolve_request_tools(params, supported_types: frozenset[type[AbstractNativeTool]], *, can_withhold_tool_schemas: Callable[[Sequence[AbstractNativeTool]], bool] | None = None, tool_addition_mode: ToolAdditionMode | None = None) -> ModelRequestParameters`.
**Data Shape:** Consumes `params.native_tools`, `params.function_tools` (ToolDefinition fields `unless_native`, `with_native`, `defer_loading`, `optional`), `revealed_tool_names`; produces filtered `native_tools` + `function_tools` and the stamped `tool_visibility: dict[str, ToolVisibility]`.

### Decisive source
```python
# models/__init__.py:1831-1859 — visibility decision table (non-deferred → 'visible' first)
if not t.defer_loading:
    visibility = 'visible'
else:
    revealed      = t.name in params.revealed_tool_names
    corpus_member = t.with_native is not None and t.with_native in supported_ids
    if corpus_member and can_defer:            visibility = 'deferred'
    elif revealed:
        if tool_addition_mode == 'with_definitions': visibility = 'via_history'
        elif can_defer:                              visibility = 'deferred'
        else:                                        visibility = 'visible'
    elif corpus_member:                          visibility = 'withheld'
    elif tool_search_on_wire:                    visibility = 'withheld'   # search indexes
                                                 #  the request's declarations — must hide
    elif tool_addition_mode == 'with_definitions': visibility = 'withheld'
    elif can_defer:                              visibility = 'deferred'   # pre-advertise:
                                                 #  nothing can leak it, stable declaration
    else:                                        visibility = 'withheld'
```

**Flow:** split natives into supported/unsupported → unsupported without fallback or optional-coverage raises UserError naming the local-fallback remedy → drop an OPTIONAL `ToolSearchTool` whose corpus is empty (`corpus_ids` from `with_native`; isinstance-confined so `WebSearchTool(optional=True)` is never dropped for mere absence of dependents) → recompute `supported_ids` AFTER the drops (rule 1 must not kill a fallback for a native that just left) → walk function tools through the table.

**Invariant:** Two narrower drops stay independent of `optional=True`: optionality governs ONLY the unsupported-native path. The corpus-empty drop is specific to framework-managed tool-search's corpus-management role — sending a searcher with nothing searchable wastes a tool slot; a non-optional ToolSearchTool stays because the user asked explicitly. Rule 2 sheds a corpus member's `with_native` when its native tool is unsupported (membership means nothing unpaired; an adapter deriving a wire flag from it would emit the flag unpaired and earn a rejection).

**Probe:** `tests/test_tool_search.py::test_optional_builtin_dropped_with_empty_corpus` (:5382), corpus-drop-with-member tests (:5320–5350: builtin+corpus both drop when unsupported; revealed member KEPT for direct local calls), `test_with_native_kept_on_supporting_model` (:5370), plus `tests/models/test_model_request_parameters.py` for the parameter-side invariants.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pydantic-ai", query: "resolve_request_tools can_withhold_tool_schemas tool_addition_mode unless_native with_native", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the full decision table including the post-drop id recomputation and the two-independent-drops rule. Adapt state names/channel modes to your transport. Omit nothing — every branch is pinned by a test that fails under the naive reordering.
