<!-- capsule-v2 -->
# Call-time tool-argument validation — who checks model-supplied args against the schema, and where is it bypassed?

**Source:** smolagents Apache-2.0 `main@30bb1161`; Codebase Memory project `smolagents`. **Question:** When a model emits a tool call, exactly which type/required checks run, with which coercions — and why can direct `tool(...)` calls skip them?

## Path/Symbol
- `src/smolagents/tools.py:validate_tool_arguments` (:1361-1412).
- Sole enforcement point: `src/smolagents/agents.py:ToolCallingAgent.execute_tool_call` (:1475-1478).
- Non-validator for comparison: `src/smolagents/tools.py:Tool.__call__` (:231-249).

## Signature
`validate_tool_arguments(tool: Tool, arguments: Any) -> None` — raises ValueError (unknown key / missing required) or TypeError (type mismatch). `execute_tool_call` translates BOTH into `AgentToolCallError(str(e), self.logger) from e`.

## Data Shape
Two passes: pass 1 iterates PROVIDED arguments; pass 2 iterates `tool.inputs`. Expected type may be str OR list of strs (list membership allowed). Non-dict `arguments` compares against the FIRST input's declared type only.

### Decisive source
```python
# tools.py:1383-1394 — pass 1 exemptions ladder
actual_type = _get_json_schema_type(type(value))["type"]
expected_type = tool.inputs[key]["type"]
expected_type_is_nullable = tool.inputs[key].get("nullable", False)
if ((actual_type != expected_type if isinstance(expected_type, str) else actual_type not in expected_type)
    and expected_type != "any"
    and not (actual_type == "null" and expected_type_is_nullable)):
    if actual_type == "integer" and expected_type == "number":
        continue                                   # silent int→number widening
    raise TypeError(f"Argument {key} has type '{actual_type}' but should be '{tool.inputs[key]['type']}'")
# :1400-1404 — pass 2: nullable ⇒ omittable
if key not in arguments and not key_is_nullable:
    raise ValueError(f"Argument {key} is required")
```

## Flow
Model call → `execute_tool_call`: unknown-tool check → `_substitute_state_variables` → **validate_tool_arguments** (errors become AgentToolCallError, i.e., coachable agent-loop errors, NOT crashes) → only then `tool(**arguments, sanitize_inputs_outputs=True)`. Runtime types are re-derived from the VALUE (`_get_json_schema_type(type(v))`) rather than trusted from JSON, so a float masquerading as int still maps correctly. `Tool.__call__` itself does NO schema validation in any mode — it only converts a single matching dict to kwargs and optionally sanitizes image/audio wrapping.

## Invariant
Validation is an AGENT-LOOP property, not a Tool property: calling `my_tool(args)` directly never type-checks. The check set is deliberately narrow — unknown keys, missing requireds, grossly wrong types, with `"any"` wildcard and null-if-nullable exemptions plus one asymmetric coercion (int widens to number; number NEVER narrows to int). Porters who move validation into `__call__` change the failure surface from "coachable loop error" to "host crash".

## Probe
`tests/test_tools.py::test_validate_tool_arguments` (:954-970) parametrizes union hints vs values incl. error expectations; `test_validate_tool_arguments_nullable` (:1035-1068) pins exact messages ("Argument param has type 'null' but should be 'string'", "Argument param is required"). Live probe: build a tool with `x: int`, call `validate_tool_arguments(tool, {"x": 1})` → passes; `{"x": 1.5}` → TypeError.

## Get live surrounding code
**Retrieve (executed 2026-08-26, project `smolagents`):**
```ts
await mcp.codebase_memory.trace_path({ project: "smolagents", function_name: "validate_tool_arguments", direction: "inbound", depth: 2 });
// callers_total=2: agents.ToolCallingAgent.execute_tool_call (sole real caller), agents.py module ref — confirming __call__ does not validate
```

## Verdict
Adopt validate-at-the-loop-boundary with error-as-data translation, and the narrow exemption ladder. Adapt the int→number widening to whatever numeric vocabulary your host uses. Omit runtime re-derivation via `_get_json_schema_type` if your calls arrive pre-typed by a strict JSON parser — but then you own the bool-is-int Python trap.
