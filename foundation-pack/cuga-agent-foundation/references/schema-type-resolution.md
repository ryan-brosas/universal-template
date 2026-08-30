<!-- capsule-v2 -->
# Ambiguity-first JSON-Schema→Pydantic typing — when must a tool parameter validate as Any instead of its "most likely" type?

**Source:** cuga-agent Apache-2.0 `main@5de53ade77c36166da6ace906af488b2b445454f`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** Your tool params come from arbitrary OpenAPI/pydantic-rendered schemas — how do you pick Python annotations that neither lie to the LLM nor reject values the real schema accepts?

## Resolve a display type through anyOf/type-arrays, but VALIDATE as Any whenever the schema is genuinely ambiguous
**Path/Symbol:** `src/cuga/backend/tools_env/registry/utils/schema_utils.py` — `_TYPE_MAPPING` :5-12, `json_schema_type` :15-35 (with the AppWorld `321ec38_1` `repeat_days` bug in docstring), `schema_type_is_ambiguous` :38-56, `python_type_for_schema` :59-69. Direct suite: `src/cuga/backend/tools_env/registry/tests/test_schema_utils.py`.
**Signature:** `json_schema_type(prop: dict, default="string") -> str`; `schema_type_is_ambiguous(prop: dict) -> bool`; `python_type_for_schema(prop: dict) -> Any` (the annotation).
**Data Shape:** pydantic renders optional fields as `anyOf: [{...}, {"type": "null"}]` with NO top-level type; OpenAPI 3.1 uses `type: ["string", "null"]`.

### Decisive source
```python
# :59-69 — the whole contract: narrow for display, Any for validation
def python_type_for_schema(prop):
    if schema_type_is_ambiguous(prop): return Any   # fail-closed validate would
    return _TYPE_MAPPING.get(json_schema_type(prop, default=""), Any)  # reject legal input
```
```python
# :38-51 — ambiguity = unresolved $ref OR >1 non-null variant;
# type:[T,"null"] stays NARROW on purpose (it's just Optional)
if isinstance(t, list): return len([x for x in t if x != "null"]) > 1
if t: return False
if "$ref" in prop: return True
for key in ("anyOf", "oneOf"):
    variants = [v for v in (prop.get(key) or []) if isinstance(v, dict) and v.get("type") != "null"]
    if len(variants) > 1: return True
```
**Flow:** renderer asks json_schema_type for the human-readable type → walks anyOf/oneOf/allOf skipping null variants (a variant with `properties` counts even without `type`) → falls back object-if-properties → default. Builder asks python_type_for_schema for the pydantic annotation → ambiguous or unknown ⇒ `Any`, so `model_validate` stays exactly as permissive as the source schema.
**Invariant:** (1) A plain `.get("type", "string")` fallback reports EVERY optional param as string — the documented production bug; never default silently. (2) Display narrowing and validation narrowing are DIFFERENT decisions with different risk: lying in docs confuses the model, over-narrow validation rejects correct calls — prefer Any there. (3) `bool` before `int` matters wherever you check isinstance order (bool subclasses int).

**Probe:** `tests/test_schema_utils.py` — `test_pydantic_optional_anyof_keeps_real_type` (:14) and siblings pin anyOf traversal; ambiguity branches pinned by unit assertions in the same suite.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "json_schema_type schema_type_is_ambiguous python_type_for_schema anyOf", limit: 8 });
```
## Verdict
Adopt the two-tier resolve/validate split for any dynamic schema ingestion. Keep the documented-bug rationale next to the code — it's why the default is "" not "string" in the builder path.
