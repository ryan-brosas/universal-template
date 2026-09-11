<!-- capsule-v2 -->
# Schema-typed coercion ladder — how do I turn untrusted form JSON into typed config without a validation framework?

**Source:** Auto_job_applier_linkedIn MIT `main@0ca5550`; Codebase Memory `Auto_job_applier_linkedIn`. **Question:** How do I coerce arbitrary JSON values (form posts) into declared field types — and where do the classic Python traps bite?

## The ladder
**Path/Symbol:** `app.py:_coerce(field_type, value)` (:113–150); consumed by `api_save_config` (:337).
**Signature:** `_coerce(field_type: str, value) -> Any` — raises `ValueError` on invalid numbers so the route can 400.
**Data Shape:** `field_type` ∈ {text, password, textarea, select, number, bool, list} matching `config_schema` declarations.

### Decisive source
```python
if field_type == "number":
    if isinstance(value, bool):
        raise ValueError("expected a number, got a boolean")
    ...
    number = float(text)
    if isinstance(number, float) and number.is_integer():
        return int(number)
    return number

if field_type == "bool":
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in ("true", "1", "yes", "on")

if field_type == "list":
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip() != ""]
    text = str(value).strip()
    if text == "":
        return []
    return [item.strip() for item in text.split(",") if item.strip() != ""]
```

**Flow:** string-ish types pass through `str()` with None→""; numbers reject bools FIRST, accept numeric strings, and snap whole floats back to int (config defaults are ints — `"25"` must not become `25.0` downstream); bools accept real booleans or the truthy-string vocabulary; lists accept either real arrays or comma-separated text, dropping empties. Unknown type passes through untouched.
**Invariant:** the `isinstance(value, bool)` guard BEFORE any numeric check is load-bearing — in Python `True` IS an `int`, so an unguarded `float(True)` yields `1.0` and a JSON `true` would silently become config value `1`. The int-snap preserves round-trip equality with module defaults (`test_config_save_coerces_and_roundtrips` asserts saved value `is True` for bools; defaults stay ints).
**Probe:** `tests/test_app_integration.py::test_config_save_coerces_and_roundtrips` (string `"true"` → stored as real `true`) + rejection tests (invalid values never reach disk).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "Auto_job_applier_linkedIn", query: "_coerce api_save_config", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the ladder shape and especially the bool-before-number guard + whole-float int-snap pair. Adapt the truthy vocabulary to your frontend's conventions. Omit the field-type names (schema-local).
