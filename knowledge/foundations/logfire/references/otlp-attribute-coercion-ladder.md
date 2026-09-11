<!-- capsule-v2 -->
# OTLP attribute coercion ladder — how do arbitrary Python values survive the OTLP wire format?

**Source:** logfire MIT `main@e484a6b5`; Codebase Memory `ext-logfire`. **Question:** What is the exact conversion applied to every attribute value before export, and where do oversized ints, NaN floats, and Enums go?

## prepare_otlp_attribute ladder + json encoder fallback
**Path/Symbol:** `logfire/_internal/main.py:prepare_otlp_attribute` (`main.py:3357-3378`) + `logfire/_internal/json_encoder.py:to_json_value` (`json_encoder.py:246-304`).
**Signature:** `prepare_otlp_attribute(value: Any) -> otel_types.AttributeValue`; `to_json_value(o: Any, seen: set[int]) -> JsonValue`.
**Data Shape:** output restricted to OTLP primitives (str/bool/int ≤2^63−1/float finite/list thereof); everything else becomes a compact JSON string.

### Decisive source
```python
if isinstance(value, Enum):
    return logfire_json_dumps(value)
elif isinstance(value, int):
    if value > OTLP_MAX_INT_SIZE:
        warnings.warn(...)   # 'larger than the maximum OTLP integer size'
        return str(value)     # int -> str, NOT json
    else:
        return value
elif isinstance(value, float):
    if not math.isfinite(value):
        return str(value)     # nan/inf -> 'nan'/'inf' strings
    return value
elif isinstance(value, (str, bool)):
    return value
else:
    return logfire_json_dumps(value)  # full recursive encoder, allow_nan=False
```
The JSON fallback (`to_json_value`) walks MRO against an `encoder_by_type()` table (sets→sorted lists w/ TypeError fallback, bytes→repr-minus-quotes, datetime→isoformat, Decimal/UUID/IP→str, pydantic models→model_dump, pandas DataFrames→head/tail summarization honoring pandas display options, numpy arrays→per-dimension head/tail clamp at 10, SQLAlchemy objects→non-deferred fields only) with a `seen: set[int]` copy-per-level circular guard emitting `'<circular reference>'`, and finally `safe_repr(o)` — repr failure itself degrades to `'<{type} object>'`.
**Flow:** Enum checked BEFORE int (IntEnum would otherwise hit the int branch and lose identity) → int overflow downgrades to string with a UserWarning → non-finite floats stringify because OTLP forbids NaN/Inf → unknown types serialize recursively with per-object-id cycle detection → total encoding failure still returns a string (repr), never raises.
**Invariant:** The function must NEVER raise — telemetry conversion sits inside `_span`'s fail-soft block but correctness depends on the always-returns-a-primitive guarantee. `allow_nan=False` in the final dumps means the float stringify above is load-bearing, not cosmetic. Note bool passes through unchanged (bool ⊄ int branch because isinstance check order matters).
**Probe:** `tests/test_json_encoder.py` + `tests/test_json_dumps.py` — pins DataFrame/numpy summarization shapes and circular-reference sentinel.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-logfire", query: "prepare_otlp_attribute OTLP_MAX_INT_SIZE logfire_json_dumps", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the ladder order (Enum→int-guard→float-guard→str/bool→JSON) and the seen-set circular protocol. Adapt the encoder table's third-party rows (pandas/numpy/pydantic) to whatever rich types your host emits. Omit the SQLAlchemy inspection arm unless you also port the ORM.
