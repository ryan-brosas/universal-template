<!-- capsule-v2 -->
# TestModel two-step state machine — how does a zero-config fake model exercise the full tool loop?

**Source:** pydantic-ai MIT `main@b3cdbc96796f0294f1ac6943cdba70d14af8a0ef`; Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai` (full mode, coverage clean). **Question:** How can an agent be end-to-end tested with NO scripted responses while still covering tool calls, retries, and output selection?

## TestModel tools-then-output simulation
**Path/Symbol:** `pydantic_ai_slim/pydantic_ai/models/test.py:TestModel._request` (:246-345), `_get_tool_calls` (:193-220), `_get_output` (:222-244), `_JsonSchemaTestData` (:440+).
**Signature:** `TestModel(call_tools='all', custom_output_text=None, custom_output_args=None, seed=0)`; `gen_tool_args(tool_def) -> Any`.
**Data Shape:** Stateless per request except `last_model_request_parameters` (last step's parameters, for assertions); args are generated from each tool's JSON schema — minimal viable data seeded by `seed` (`const`/`enum`/`examples` first, then required-only object properties, `$ref` resolved through `$defs`).

### Decisive source
```python
# test.py:260-267 — step 1: if NO ModelResponse in history yet, call ALL callable tools at once
if tool_calls and not any(isinstance(m, ModelResponse) for m in messages):
    return ModelResponse(
        parts=[ToolCallPart(name, self.gen_tool_args(args), tool_call_id=f'pyd_ai_tool_call_id__{name}')
               for name, args in tool_calls],
        model_name=self._model_name)

# test.py:198-202 — 'via_history' deferred-revealed tools ARE callable; only 'withheld' invisible
callable_function_tools = [
    tool for tool in model_request_parameters.function_tools
    if model_request_parameters.visibility_of(tool.name) != 'withheld'
]

# test.py:274-296 — retry prompts replay ONLY the named tools; output-tool retries prefer
# custom_output_args over regenerated schema data
new_retry_names = {p.tool_name for p in last_message.parts if isinstance(p, RetryPromptPart)}
```

**Flow:** Step 1: any function/output tools declared → one `ModelResponse` calling all of them simultaneously (deterministic ids `pyd_ai_tool_call_id__<name>`) → agent executes → returns real `ToolReturnPart`s → Step 2 (no more tools to call): collect every tool return into a JSON dict emitted as `TextPart`, or `'success (no tool calls)'` if none. Overrides: `custom_output_text` asserts text mode is legal; `custom_output_args` targets `output_tools[0]` wrapped under `outer_typed_dict_key`; without overrides the output tool is chosen by `seed % len(output_tools)`. Retry prompts in the last message cause ONLY the retried tools to be re-called.
**Invariant:** The state machine is driven by message HISTORY shape ("has any ModelResponse been emitted?"), not counters — so it composes with multi-step runs and retries without bookkeeping. Named `call_tools` entries that exist but are withheld/deferred raise a UserError telling the user to reveal them first (:212-219); unknown names raise separately.
**Probe:** `tests/models/test_model_test.py::test_call_one` (:73), `::test_call_hidden_tool_has_clear_error` (:92), `::test_custom_output_text` (:168), `::test_json_schema_test_data` (:469).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pydantic-ai", query: "TestModel gen_tool_args JsonSchemaTestData call_tools", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the history-driven two-step simulator and schema-derived minimal args as the default no-config test model for any agent framework; adapt the visibility rules to your deferral story; omit native-tool emulation (TestModel rejects builtin tools outright). Caveat: source read at HEAD this session.
