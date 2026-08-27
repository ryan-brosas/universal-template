<!-- capsule-v2 -->
# Tool schema & run gate — how do tools declare LLM-visible schemas and validate model-supplied arguments?

**Source:** autogen (MIT — LICENSE-CODE) `main@027ecf0a379bcc1d09956d46d12d44a3ad9cee14`; Codebase Memory project `autogen` (FULL, 16,432 nodes / 86,358 edges, generation 2026-08-24T16:12:29Z). **Question:** Where is the boundary between "what the model sees" and "what actually executes", and when does strict mode fail?

## Schema at declaration time; strict fails lazily; validation gates execution
**Path/Symbol:** `python/packages/autogen-core/src/autogen_core/tools/_base.py` (`BaseTool.schema` :115–148, `run_json` :179–208); `python/packages/autogen-core/src/autogen_core/tools/_function_tool.py` (`FunctionTool.__init__` :88–103). Sole production `run_json` caller: `AssistantAgent._execute_tool_call` (trace callers_total=1).
**Signature:** `def schema(self) -> ToolSchema` / `async def run_json(self, args: Mapping[str, Any], cancellation_token: CancellationToken, call_id: str | None = None) -> Any`.
**Data Shape:** `ToolSchema{name, description, parameters: {type:"object", properties, required, additionalProperties}, strict}`. Args types are pydantic BaseModels — hand-written for class tools, SYNTHESIZED from a function's typed signature for `FunctionTool` (`args_base_model_from_signature`; Annotated descriptions ride into properties).

### Decisive source
```python
# schema(): pydantic → JSON schema → $defs inlined via jsonref → strict asserts
model_schema = self._args_type.model_json_schema()
if "$defs" in model_schema:
    model_schema = jsonref.replace_refs(obj=model_schema, proxies=False)
    del model_schema["$defs"]
...
if self._strict and set(parameters["required"]) != set(parameters["properties"].keys()):
    raise ValueError("Strict mode is enabled, but not all input arguments are marked as required. ...")
if self._strict and parameters["additionalProperties"]:
    raise ValueError("Strict mode is enabled but additional argument is also enabled. ...")

# run_json(): VALIDATION GATE before execution
with trace_tool_span(tool_name=self._name, tool_description=self._description, tool_call_id=call_id):
    return_value = await self.run(self._args_type.model_validate(args), cancellation_token)
```

**Flow:** construct tool (FunctionTool synthesizes its args BaseModel + detects `"cancellation_token"` param for cancellation support) → host reads `.schema` to advertise tools to the model → model returns JSON args → `_execute_tool_call` calls `run_json` → `model_validate(args)` rejects malformed payloads with a pydantic ValidationError BEFORE `run()` executes → result stringified into ToolCallEvent logs with RAW args.
**Invariant:** strict-mode violations surface only when `.schema` is ACCESSED, never at construction — a strictly-invalid tool constructs fine and explodes at advertisement time. Strict requires ALL properties required (default arguments banned) AND `additionalProperties=False`. Schema generation inlines `$defs` so providers never see local references.
**Probe:** `python/packages/autogen-core/tests/test_tools.py::test_func_tool_schema_generation_strict` (:97–125 — default-arg function raises `ValueError, match="Strict mode..."` on `.schema`; strict-valid function pins `required == ["arg", "other"]` and `additionalProperties is False`) and `::test_func_tool_schema_generation_only_default_arg_strict` (:146–152).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "autogen", query: "BaseTool schema run_json args_type strict ToolSchema FunctionTool", file_pattern: "*tool*", limit: 20 });
```

## Verdict
Adopt declaration-time schema generation with a validating run gate so malformed model output can never reach tool bodies with raw dicts. Adapt where strict violations surface (construction-time check is friendlier if you control tool registration). Omit jsonref inlining if your provider accepts `$defs`/`$ref` natively.
