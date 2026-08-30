<!-- capsule-v2 -->
# JSON schema sidecar attributes — how does the backend learn each attribute's Python type without a schema registry?

**Source:** logfire MIT `main@e484a6b5`; Codebase Memory `ext-logfire`. **Question:** When is `logfire.json_schema` attached, what shape does it take, and how do dict/array schemas scale with size?

## create_json_schema + attributes_json_schema_properties
**Path/Symbol:** `logfire/_internal/json_schema.py:create_json_schema` (`json_schema.py:99-156`), `_mapping_schema` (`json_schema.py:243-267`), `_array_schema` (`json_schema.py:270-306`).
**Signature:** `create_json_schema(obj, seen) -> JsonDict`; attribute value = `dump_json({'type':'object','properties':{attr: schema}})`; custom keywords all prefixed `x-` (`x-python-datatype`, `x-columns`, `x-indices`, `x-shape`, `x-dtype`, …).

### Decisive source
```python
if obj_type in {str, int, bool, float}:
    return {}                                   # plain scalars carry NO schema entry at all
...
# mapping scaling:
n = len(obj); has_long_key = any(len(str(k)) > 100 for k in obj.keys()); is_large = n > 100 or has_long_key
if n <= 10 and not has_long_key:
    schema.update(_properties(...))             # small dict: per-key properties
else:
    common_schema, is_homogeneous = _check_homogeneous(obj, seen)
    if is_homogeneous and common_schema is not None and common_schema not in PLAIN_SCHEMAS:
        schema['additionalProperties'] = common_schema   # homogeneous: one shared schema
    elif not is_large:
        schema.update(_properties(...))         # medium heterogeneous: still per-key
    # else large heterogeneous → just {'type': 'object'} (drop schema)
```
Array analog: homogeneous ⇒ `items`; heterogeneous ⇒ full `prefixItems`; PLAIN_SCHEMAS items (`{}`, object, array, null) are omitted from properties because "the frontend can just render them as plain JSON"; sets sorted (TypeError → unsorted fallback). MRO walk against `type_to_schema()` table covers datetime/Decimal/UUID/Enum/pydantic/numpy/pandas before falling to `{'type':'object','x-python-datatype':'unknown'}`.
Attachment points: `_span`/`log()` compute properties from USER attributes only (EXCLUDE_KEYS strips stack-info + scrubbed metadata); `LogfireSpan.set_attribute` marks `_added_attributes=True` so `_end` attaches the UPDATED schema just before ending; `set_user_attributes_on_raw_span` MERGES with existing properties parsed from the current span attr.
**Flow:** construction-time schema computed once per span/log from declared kwargs → post-enter set_attribute extends the property map → end-time re-serialization only when dirty. Backend uses x-python-datatype to reconstruct typed columns/UI rendering.
**Invariant:** Plain-scalar omission keeps the sidecar small — schema presence itself signals "interesting type". The homogeneity check recurses over values, so its cost is bounded by the same seen-set discipline as encoding.
**Probe:** `tests/test_json_schema.py` — pins scalar omission, prefixItems vs items selection, size thresholds.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-logfire", query: "create_json_schema _mapping_schema _array_schema attributes_json_schema", limit: 8, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt inline-schema-sidecar pattern with scalar omission and size-tiered dict/array shapes for any columnar telemetry store. Adapt x-key vocabulary to your renderer. Omit SQLAlchemy/attrs arms if absent in host.
