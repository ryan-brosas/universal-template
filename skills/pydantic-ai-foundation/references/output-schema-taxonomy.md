<!-- capsule-v2 -->
# OutputSchema.build — sentinel-peeling dispatch into the schema taxonomy

**Source:** pydantic-ai (MIT) `main@b3cdbc96796f0294f1ac6943cdba70d14af8a0ef`; Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai`. **Question:** How does a user-supplied output spec (types, markers, None, images, deferred tools) get compiled into exactly one runtime OutputSchema variant, and which combinations are illegal?

## OutputSchema.build compile ladder
**Path/Symbol:** `pydantic_ai_slim/pydantic_ai/_output.py:OutputSchema.build` (449-607), `_build_processor` (609-620); result classes `TextOutputSchema`/`ToolOutputSchema`/`AutoOutputSchema`/`NativeOutputSchema`/`PromptedOutputSchema`/`ImageOutputSchema` (623+).
**Signature:** `build(output_spec: OutputSpec[T], *, name=None, description=None, strict=None) -> OutputSchema[T]`.
**Data Shape:** flattened outputs list; sentinel flags peeled off (`allows_none`, `allows_deferred_tools`, `allows_image`); marker classes `NativeOutput`/`PromptedOutput`/`TextOutput`/`ToolOutput`.

### Decisive source
```python
outputs = _flatten_output_spec(output_spec)
allows_none = NoneType in outputs or None in outputs   # str|None vs bare None both peel
if allows_none: outputs = [o for o in outputs if o is not NoneType and o is not None]
if allows_deferred_tools: outputs = [o for o in outputs if o is not DeferredToolRequests]
if allows_image: outputs = [o for o in outputs if o is not BinaryImage]

# marker classes must be ALONE (their payload flattened separately):
if output := next((o for o in outputs if isinstance(o, NativeOutput)), None):
    if len(outputs) > 1: raise UserError('`NativeOutput` must be the only output type.')
    # ... and cannot CONTAIN DeferredToolRequests / BinaryImage either

# None becomes its own tool so the model can commit to None via the structured schema:
if allows_none and (tool_outputs or other_outputs): other_outputs.append(NoneType)

toolset = OutputToolset.build(tool_outputs + other_outputs, ...)
# dispatch tail:
text + toolset  -> ToolOutputSchema(text_processor=..., toolset=...)
text alone      -> TextOutputSchema
tool only       -> ToolOutputSchema
other types     -> AutoOutputSchema(processor=(single ? Object : Union), toolset=...)  # toolset set defensively
image only      -> ImageOutputSchema
nothing         -> UserError('At least one output type must be provided.')
```

**Flow:** flatten → peel sentinels into boolean capabilities → enforce single-marker rules → bucket remaining outputs into text/tool/other → expose NoneType as an output tool when None coexists with structured outputs → dispatch to exactly one schema class; single-output processors become `ObjectOutputProcessor`, multiples become `UnionOutputProcessor`.
**Invariant:** Sentinel flags are peeled BEFORE bucketing so they never leak into processor construction. Marker classes (`NativeOutput`, `PromptedOutput`) are exclusive — mixing them with other outputs is a UserError at build time, not a runtime surprise. `AutoOutputSchema` always carries its toolset even when the resolved mode might not need it (mode unknown at agent-construction time; conflict checking happens in the Agent constructor). Empty-after-peel is an error, never a silent text fallback.
**Probe:** `tests/test_output.py` (build-ladder and exclusion tests); union/single processor split pinned by `_build_processor` tests.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pydantic-ai", query: "OutputSchema.build NativeOutput PromptedOutput AutoOutputSchema flatten", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the peel-then-bucket-then-dispatch shape and exclusive-marker validation; adapt the schema-class taxonomy to your host's output modes; omit pydantic-specific type flattening. Extends `output-schema-build.md`'s pass-2 view with the full class-dispatch tail. Coverage clean.
