<!-- capsule-v2 -->
# Strict JSON-schema conversion — how is an arbitrary JSON schema made OpenAI-strict WITHOUT changing accepted values?

**Source:** OpenAI Agents Python MIT `main@cb8a2e7e`; Codebase Memory project `openai-agents-python`. **Question:** What are the mutation rules, the failure conditions, and the DoS guards in `ensure_strict_json_schema`?

## Strict converter + node budget
**Path/Symbol:** `src/agents/strict_schema.py:` `ensure_strict_json_schema` (:115–134), `_ensure_strict_json_schema` (:155–405), `_NodeBudget` (:98–112), `_MAX_SCHEMA_NODES = 100_000` (:21), `resolve_ref` (:408–424).
**Signature:** `def ensure_strict_json_schema(schema: dict[str, Any], *, _reject_open_objects: bool = False) -> dict[str, Any]`.
**Data Shape:** mutates a deep copy in place; empty schema → fresh `{type: object, properties: {}, required: [], additionalProperties: False}`; budget counts every visited node incl. `$defs`.

### Decisive source
```python
elif (
    is_object and "additionalProperties" in json_schema
    # Compare with ``is not False`` rather than truthiness: OpenAPI/MCP schemas often use
    # ``additionalProperties: {}`` (an empty schema meaning "allow anything"). That value is
    # falsy in Python, so a truthiness check would silently leave a non-strict schema in place.
    and json_schema["additionalProperties"] is not False
):
    raise UserError(_ADDITIONAL_PROPERTIES_ERROR)
...
json_schema["required"] = list(properties.keys())   # strict mode: every property required
```
Other rules: root must be non-nullable object (`anyOf` at root rejected); `oneOf` folded into `anyOf` (structured outputs lack nested oneOf); singleton `allOf` merged via `_merge_single_all_of` with explicit incompatible-overlap detection (`properties: {}` / `required: []` parents are no-ops; equality is type-strict — bool ≠ int); `$ref` with constraining siblings raises instead of merging (only annotation keywords allowed alongside, root additionally allows `$id`); ref chains resolved with JSON-pointer `~0/~1` unescaping and cycle detection; nested `$id` resources refuse ref resolution across the resource boundary.

**Flow:** depth-validate iteratively BEFORE deepcopy (max 100) → budget-guarded recursive walk → per node: normalize typeless-property objects to object → close objects / reject open ones (opt-in) → required-from-properties → recurse into properties/items/anyOf → fold oneOf → merge singleton allOf (re-run on merged result) → strip `default: None` → inline refs whose schema carries extra keys (local keys WIN over ref'd ones) → re-strictify the inlined result.

**Invariant:** Conversion must never change the language of accepted values — anything ambiguous fails LOUD as `UserError` rather than approximating; expansion cost is bounded because third-party schemas (e.g. MCP servers) are untrusted input.

**Probe:** `tests/test_strict_schema.py::test_deeply_nested_schema_is_rejected_before_recursive_conversion` (:61), `test_allOf_single_ref_chain_spends_node_budget` (:516), `test_object_with_empty_dict_additional_properties` (:258); sibling suite `tests/test_strict_schema_oneof.py`; failed MCP conversion keeps the ORIGINAL schema (`tests/mcp/test_mcp_util.py:1902`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "openai-agents-python", query: "ensure strict json schema node budget additionalProperties", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt for any structured-output/tool-schema path targeting strict-mode providers; adapt the sibling allowlist to your dialect; omit oneOf-folding if your provider accepts it natively. The `is not False` trap and fail-loud rule are directly portable.
