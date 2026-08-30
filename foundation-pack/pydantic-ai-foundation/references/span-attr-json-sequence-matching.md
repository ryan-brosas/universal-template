<!-- capsule-v2 -->
# Attribute matching over hostile stored values — how do you match attributes that instrumentation libraries stored as JSON strings or the SDK stored as tuples, without crashing on bad data?

**Source:** pydantic-ai MIT `main@a5b5fb7a247f863599d61dfa9159bc2ebc786255` (pydantic_evals); Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai`. **Question:** OTel span attributes can only hold primitives or sequences thereof, so Logfire stores dict/list values as JSON STRINGS and the OTel SDK stores sequence values as TUPLES. A porter writing a query matcher must decide which coercions are safe, which direction they flow, and what happens when the stored string is invalid JSON or pathologically nested.

## Three-step coercion ladder with a RecursionError guard
**Path/Symbol:** `pydantic_evals/pydantic_evals/otel/span_tree.py:SpanNode._attribute_matches` (:259-274), called from `_matches_query`'s `has_attributes` condition (:301-304).
**Signature:** `_attribute_matches(self, key: str, expected: Any) -> bool`.
**Data Shape:** `self.attributes: dict[str, AttributeValue]` where `AttributeValue = str | bool | int | float | Sequence[str|bool|int|float]`; query-side `expected` may be any of those PLUS dict/list (the shapes instrumentation serialized away).

### Decisive source
```python
def _attribute_matches(self, key: str, expected: Any) -> bool:
    """Check if a span attribute matches an expected value, handling JSON-serialized dicts and lists."""
    stored = self.attributes.get(key)
    if stored == expected:
        return True
    # OTel attribute values can only be primitives or sequences thereof, so instrumentation
    # libraries like Logfire store dict and list values as JSON strings.
    if isinstance(expected, dict | list) and isinstance(stored, str):
        try:
            return json.loads(stored) == expected
        except (json.JSONDecodeError, RecursionError):
            return False
    # The OTel SDK stores sequence attribute values as tuples
    if isinstance(expected, list) and isinstance(stored, tuple):
        return list(stored) == expected
    return False
```

**Flow:** step 1 plain equality (fast path, covers all same-type matches including missing key → `None != expected`). Step 2 only when the QUERY side is dict|list and the STORED side is str: parse and compare; both `JSONDecodeError` AND `RecursionError` return False — `'[' * 10000` must not crash an evaluator mid-run. Step 3 only when the query side is list and the stored side is tuple: compare via `list(stored)`. Anything else is False.
**Invariant:** coercion flows ONE direction only — query-shape → stored-shape. A stored STRING is never deserialized against a PRIMITIVE query: `'42'` does not match `42`, `'true'` does not match `True`. Reversing that would make every numeric-string attribute match its parsed value and silently corrupt filters. And any parse failure is a NON-MATCH, never an exception — matching runs inside evaluator assertions where a crash would fail the whole evaluation.
**Probe:** `tests/evals/test_otel.py::test_span_node_matches_json_serialized_attributes` (:238-282) pins dict/list-query vs JSON-string storage, the primitive non-deserialization asymmetry (`numeric_str='42'` vs 42, `bool_str='true'` vs True), invalid-JSON non-match, and the `'['*10000` deep-nesting no-crash case; `test_span_node_matches_native_sequence_attributes` (:284-300) pins list-query vs tuple-stored via a raw OTel tracer. Suite EXECUTED GREEN at pin this pass (29 passed).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pydantic-ai", query: "_attribute_matches has_attributes json", limit: 10, fields: ["signature", "name", "file"] });
```
Live check this pass: Codebase Memory MCP was unreachable in this session (stdio env reference unavailable at transport open); anchors confirmed by direct read of span_tree.py :259-274/:301-304 at pin `a5b5fb7a` (zero drift, clean tree).

## Verdict
Adopt the ladder verbatim for ANY matcher over a storage layer that coerces rich values into strings/tuples: plain-equality fast path → shape-gated deserialization → container-type normalization → False. Adopt the one-direction rule (never deserialize stored primitives against typed queries) and the catch-RecursionError guard for untrusted stored text. Adapt the shape gates to your storage's actual serialization (e.g. msgpack instead of JSON); omit step 3 if your SDK stores lists as lists. Coverage caveat: none — span_tree.py read whole this pass.
