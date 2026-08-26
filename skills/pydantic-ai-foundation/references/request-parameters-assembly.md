<!-- capsule-v2 -->
# _prepare_request_parameters — graph-side request assembly with the corpus-empty native-tool drop

**Source:** pydantic-ai (MIT) `main@b3cdbc96796f0294f1ac6943cdba70d14af8a0ef`; Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai`. **Question:** How does the agent graph assemble `ModelRequestParameters` from the tool manager — splitting function vs output tools, resolving dynamic native tools, and when must an auto-injected ToolSearchTool be dropped BEFORE model resolution?

## _prepare_request_parameters assembly
**Path/Symbol:** `pydantic_ai_slim/pydantic_ai/_agent_graph.py:_prepare_request_parameters` (764-843); consumer `models.Model.prepare_request` (see `prepare-request-normalization.md`).
**Signature:** `async _prepare_request_parameters(ctx, instruction_parts) -> ModelRequestParameters`.
**Data Shape:** inputs: tool_manager.tool_defs (already reflects prepare_tools/prepare_output_tools capability hooks), ctx.deps.native_tools (static or factory), run_context.capabilities; output: function_tools / output_tools / native_tools / deferred_capability_ids / revealed_tool_names / output-mode fields.

### Decisive source
```python
# prepare_tools/prepare_output_tools are ALREADY baked into tool_manager.tool_defs
for tool_def in ctx.deps.tool_manager.tool_defs:
    (output_tools if tool_def.kind == 'output' else function_tools).append(tool_def)

# dynamic native tools: factories may be sync/async and may return None
raw = list(ctx.deps.native_tools)
for tool in raw:
    if isinstance(tool, AbstractNativeTool): native_tools.append(tool)
    else:
        t = tool(run_context)
        if inspect.isawaitable(t): t = await t
        if t is not None: native_tools.append(t)

has_tool_search_corpus = any(t.with_native == ToolSearchTool.kind for t in function_tools)
if not has_tool_search_corpus:
    # drop ONLY optional, auto-injected ToolSearchTools. Rationale: instrumentation and
    # durable-exec payloads observe parameters BEFORE Model.prepare_request resolution,
    # so filtering here too keeps the observed request shape honest. Non-optional
    # ToolSearchTools (user-passed) SURVIVE so unsupported models still fail loudly.
    native_tools = [t for t in native_tools if not (isinstance(t, ToolSearchTool) and t.optional)]
# NOTE: other optional native tools (e.g. hypothetical WebSearchTool(optional=True)) have no
# corpus and must NOT be dropped here — they drop on the unsupported-model path instead.

deferred_capability_ids = {cid for cid, cap in run_context.capabilities.items() if cap.defer_loading is True}
return ModelRequestParameters(
    ...,
    revealed_tool_names=_revealed_tool_names(          # keep discovered names NOT in current defs
        run_context.discovered_tool_names, function_tools,
        deferred_capability_ids=deferred_capability_ids,
        loaded_capability_ids=run_context.loaded_capability_ids),
    output_mode=output_schema.mode, ...)
```

**Flow:** split defs by kind → resolve native-tool factories → drop corpus-less auto-injected search tools → compute deferred-capability ids → preserve discovered-but-undefined reveal names → emit parameters consumed later by the model's profile-driven normalization.
**Invariant:** The corpus-empty drop is scoped to `ToolSearchTool` + `optional` only — a porter who generalizes it to all optional native tools breaks tools whose support check belongs at the provider layer. The drop happens in BOTH places (graph assembly AND `Model.prepare_request`) precisely because some observers see parameters pre-resolution. Capability `prepare_*` hooks are baked upstream; this function never re-runs them.
**Probe:** `tests/test_tool_search.py::test_search_corpus_includes_already_discovered_tools` (959) and tool-search eval matrix (511+) pin the corpus-drop behavior; `tests/test_capabilities.py` pins hook-baked tool_defs.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pydantic-ai", query: "_prepare_request_parameters ToolSearchTool optional native_tools revealed_tool_names", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the two-stage drop discipline (assembly-time honesty + model-time resolution) and the strict scoping rule; adapt parameter field names to your request type; omit the durable-exec observer rationale if your host has no pre-resolution observers. Complements `prepare-request-normalization.md` (model side). Coverage clean.
