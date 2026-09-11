<!-- capsule-v2 -->
# Type-hint → JSON-schema vocabulary ladder — what does each Python annotation become, and where are the traps?

**Source:** smolagents Apache-2.0 `main@30bb1161`; Codebase Memory project `smolagents`. **Question:** How do Python type hints map to the closed tool-type vocabulary without pydantic, and which hints are rejected or silently degraded?

## Path/Symbol
- `src/smolagents/_function_type_hints_utils.py:_convert_type_hints_to_json_schema` (:291-323), `_parse_type_hint` (:326-384), `_parse_union_type` (:387-400), `_BASE_TYPE_MAPPING` (:403-412), `_get_json_schema_type` (:415-431).

## Signature
`_parse_type_hint(hint: type) -> dict`; `_parse_union_type(args: tuple[Any, ...]) -> dict`; `_get_json_schema_type(param_type) -> dict[str,str]`.

## Data Shape
Base mapping: int→integer, float→number, str→string, bool→boolean, list→array, dict→object, Any→"any", NoneType→null. Output dicts may carry `nullable`, `enum`, `items`, `prefixItems`, `additionalProperties`, `anyOf`, or a type LIST (sorted basic union). Vocabulary matches `tools.AUTHORIZED_TYPES` (tools.py:82-93).

### Decisive source
```python
# :311-315 — default ⇒ nullable; missing hint gated by flag
if param.default == inspect.Parameter.empty: required.append(param_name)
else: properties[param_name]["nullable"] = True
# :391-400 — union folding + None detection
elif all(isinstance(subtype["type"], str) for subtype in subtypes):
    return_dict = {"type": sorted([subtype["type"] for subtype in subtypes])}
else: return_dict = {"anyOf": subtypes}
if type(None) in args: return_dict["nullable"] = True
# :418-431 — multimodal specials and silent object fallback
if str(param_type) == "Image": ... return {"type": "image"}
if str(param_type) == "Tensor": ... return {"type": "audio"}   # NOTE: audio, not image!
return {"type": "object"}                                      # unknown class → silent object
```

## Flow
`get_type_hints(func)` drives properties; `inspect.signature` decides `required`. Ladder per hint: no origin → base mapping (KeyError → `TypeHintParsingException`); Union/`|` → fold; list → recurse single item arg (`list` bare → plain array); tuple → `prefixItems` but ONE-element tuples AND `...` are hard-rejected with coaching text ("use List[] instead"); dict → `{type:object}` + `additionalProperties:<value-type>` only (KEY type is dropped); Literal → union of member runtime types + `enum` minus Nones. Return position: multi-type union is coerced to `"any"` (:317-321). PIL `Image` and torch `Tensor` are special-cased behind `str(param_type)` name gates with real equality checks and lazy imports (torch miss falls through to object).

## Invariant
`Optional[X] == X | None == default-value` in schema terms: ALL THREE set `nullable:true`, but they mean different things at call time (see nullable-semantics-overload capsule). Unknown custom classes do NOT fail here when reached via `_get_json_schema_type` — they silently become `{"type":"object"}`; only origin-less misses in `_parse_type_hint` raise. Tuple[one] and Ellipsis raise loudly rather than degrade.

## Probe
`tests/test_function_type_hints_utils.py::TestGetJsonSchema`: test_get_json_schema_example (:242-271) pins `tuple[str,str,float]|None → {array, prefixItems[3], nullable:true}`; test_optional_types (:360-370) pins default⇒nullable + not-required; test_union_types (:379-387) pins param union→2-type list and RETURN union→"any"; test_complex_types (:346-358) pins prefixItems element order. Live probe: annotate an arg `x: SomeCustomClass` → property becomes `"type":"object"` with no error.

## Get live surrounding code
**Retrieve (executed 2026-08-26, project `smolagents`):**
```ts
await mcp.codebase_memory.search_graph({ project: "smolagents", query: "_parse_type_hint union optional literal tuple prefixitems nullable base type mapping", limit: 10 });
// top rows: _get_json_schema_type :415-431, _parse_type_hint :326-384, _convert_type_hints_to_json_schema :291-323 (+ TestGetJsonSchema tests)
```

## Verdict
Adopt the ladder shape (origin dispatch + union folding + nullable-on-default) as a pydantic-free schema builder. Adapt the vocabulary names to your host. Omit the torch-Tensor→"audio" surprise unless you share smolagents' multimodal convention — port it consciously or you will mislabel tensor inputs.
