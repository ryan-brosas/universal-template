<!-- capsule-v2 -->
# OutputSchema.build — how an output SPEC becomes modes, markers, and the deferred/image carve-outs

**Source:** pydantic-ai MIT `main@b3cdbc96796f0294f1ac6943cdba70d14af8a0ef`; Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai` (full mode, coverage clean). **Question:** How does a framework turn a user's `output_type=[A, str, ToolOutput(B), None]`-style spec into a resolved schema with exactly one structured strategy?

## OutputSchema.build dispatch ladder
**Path/Symbol:** `pydantic_ai_slim/pydantic_ai/_output.py:OutputSchema.build` (:450-607), `_flatten_output_spec` (:1545-1560), marker classes in `output.py` (`ToolOutput` :77-150, `NativeOutput` :153-205, `PromptedOutput` :208-275, `TextOutput` :320-349).
**Signature:** `OutputSchema.build(output_spec, *, name=None, description=None, strict=None) -> OutputSchema[T]`; `_flatten_output_spec` recurses sequences AND peels typing unions via `get_union_args`.
**Data Shape:** Result is one of `TextOutputSchema | ImageOutputSchema | NativeOutputSchema | PromptedOutputSchema | ToolOutputSchema | AutoOutputSchema`, each carrying `allows_none / allows_deferred_tools / allows_image` flags plus optional `text_processor` and/or output `toolset`.

### Decisive source
```python
# _output.py:461-472 — control-flow types are peeled from the spec BEFORE mode resolution
allows_none = NoneType in outputs or None in outputs
if allows_none:
    outputs = [o for o in outputs if o is not NoneType and o is not None]
    if len(outputs) == 0:
        raise UserError('At least one output type must be provided other than `None`.')
allows_deferred_tools = DeferredToolRequests in outputs
...
allows_image = _messages.BinaryImage in outputs

# _output.py:478-487 — native/prompted are exclusive strategies, and the envelope can't hide inside
if output := next((output for output in outputs if isinstance(output, NativeOutput)), None):
    if len(outputs) > 1:
        raise UserError('`NativeOutput` must be the only output type.')
    flattened_outputs = _flatten_output_spec(output.outputs)
    if DeferredToolRequests in flattened_outputs:
        raise UserError('`NativeOutput` cannot contain `DeferredToolRequests`. Include it alongside ...')

# _output.py:554-555 — None becomes its OWN tool so the model can commit to it under tool mode
if allows_none and (tool_outputs or other_outputs):
    other_outputs.append(cast(OutputTypeOrFunction[OutputDataT], NoneType))
```

**Flow:** Flatten spec (recursion + union peel) → peel the three control-flow sentinels (`NoneType`, `DeferredToolRequests`, `BinaryImage`) into boolean flags → if a Native/Prompted marker exists it must be ALONE (its inner list re-flattened; envelope/image inside it rejected with a fix-it message) → classify remaining items into text (`str`/`TextOutput`), `ToolOutput` wrappers, or bare types → text + tools ⇒ hybrid `ToolOutputSchema(text_processor=…)`; text alone ⇒ `TextOutputSchema`; tools ⇒ `ToolOutputSchema`; bare types only ⇒ `AutoOutputSchema` (resolves per-model at request time but registers its toolset early for name-conflict checking); image-only ⇒ `ImageOutputSchema`.
**Invariant:** (1) Sentinel flags are computed ONCE at build time — every downstream consumer (`run_none_process_hooks`, image hooks, deferred emission) reads `schema.allows_*` rather than rescanning the spec. (2) At most one text source and one native/prompted strategy may exist. (3) `AutoOutputSchema` sets `text_processor=processor` so "structured" primitives still parse model TEXT when the chosen mode is prompted/native.
**Probe:** `tests/test_agent_output_schemas.py::test_native_output_union_preserves_description` (:197); construction-time rejection tests `tests/test_agent.py:2002/2020` (envelope vs Native/Prompted); `tests/test_agent.py::test_output_type_native_output_with_deferred_tool_requests`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pydantic-ai", query: "OutputSchema build AutoOutputSchema ToolOutputSchema flatten_output_spec", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the sentinel-peeling build ladder and single-strategy enforcement; adapt marker-class names to your API surface; omit the auto/per-model resolution branch if your host always knows the model up front. Caveat: source read at HEAD this session.
