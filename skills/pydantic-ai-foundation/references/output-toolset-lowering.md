<!-- capsule-v2 -->
# OutputToolset build — output types as tools: naming, dedup, and retry overrides

**Source:** pydantic-ai MIT `main@b3cdbc96796f0294f1ac6943cdba70d14af8a0ef`; Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai` (full mode, coverage clean). **Question:** How do declared output types become callable tools with deterministic names and per-tool retry budgets?

## OutputToolset.build
**Path/Symbol:** `pydantic_ai_slim/pydantic_ai/_output.py:OutputToolset` (:1395-1532; `build` :1409-1487, `get_tools` :1514-1525, `call_tool` backstop :1527-1532).
**Signature:** `build(outputs, *, name=None, description=None, strict=None) -> OutputToolset | None`; `ToolDefinition(name, description, parameters_json_schema, strict, outer_typed_dict_key, kind='output', sequential=…)`.
**Data Shape:** `processors: dict[name → ObjectOutputProcessor]`, `_tool_defs: list[ToolDefinition]`, `max_retries` (agent default, set pre-run), `_max_retries_overrides: dict[name → int]` from `ToolOutput(max_retries=N)`.
**Data Shape (naming):** Single output ⇒ `name or 'final_result'`; multiple ⇒ `'final_result' + '_' + sanitized type name` (`TOOL_NAME_SANITIZER` strips generic brackets); collisions deduped `_2`, `_3`…

### Decisive source
```python
# _output.py:1453-1464 — deterministic naming with sanitizer + collision suffixes
if name is None:
    name = default_name
    if multiple:
        # strip unsupported characters like "[" and "]" from generic class names
        safe_name = _utils.TOOL_NAME_SANITIZER.sub('', object_def.name or '')
        name += f'_{safe_name}'
i = 1
original_name = name
while name in processors:
    i += 1
    name = f'{original_name}_{i}'

# _output.py:1514-1523 — per-tool override wins over agent default; assert catches unwired runs
async def get_tools(self, ctx):
    assert self.max_retries is not None, 'Agent must set OutputToolset.max_retries before the run'
    max_retries = self.max_retries
    return {tool_def.name: ToolsetTool(
        toolset=self, tool_def=tool_def,
        max_retries=self._max_retries_overrides.get(tool_def.name, max_retries),
        args_validator=self.processors[tool_def.name].validator,
    ) for tool_def in self._tool_defs}
```

**Flow:** For each output spec item: unwrap `ToolOutput` options → build an `ObjectOutputProcessor` (which computes the JSON schema, description fallback chain docstring → default 'The final response which ends this conversation', prefixed by the type name when multiple) → resolve final name/description/strict → emit a `kind='output'` ToolDefinition carrying `outer_typed_dict_key` so executors know to unwrap `{'response': …}` shapes and `sequential` so exhaustive-strategy scheduling treats it as a barrier. At runtime these tools flow through `validate_output_tool_call`/`execute_output_tool_call` — NOT the normal toolset `call_tool` path, which raises NotImplementedError as a wiring backstop.
**Invariant:** The retry budget for outputs is a SEPARATE axis (agent `max_output_retries` defaulting per-tool overrides) — reusing the function-tool budget here would couple unrelated retry loops. Naming must be deterministic across runs: schema-derived names feed history replay where a mismatched id would orphan prior calls.
**Probe:** `tests/models/test_model_test.py::test_output_type` (:279 — generated output-tool call shape), `tests/test_usage_limits.py::test_output_tool_not_counted` (:793 — output tools excluded from tool_calls usage).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pydantic-ai", query: "OutputToolset build final_result max_retries_overrides", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt output-as-tool lowering with sanitized deterministic names, per-tool retry overrides over a run default, and the kind='output' marker separating execution paths; adapt naming defaults; omit the sequential/barrier flag if you lack parallel end strategies. Caveat: source read at HEAD this session.
