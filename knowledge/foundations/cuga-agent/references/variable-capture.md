<!-- capsule-v2 -->
# VariableUtils — JSON-safe variable capture: tagged envelopes for sets/tuples/DataFrames, identity-preserving hydration

**Source:** cuga-agent Apache-2.0 `main@5de53ade`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** An agent carries variables between code blocks through checkpointed LangGraph state (JSON-only). How do round-trip values that JSON cannot represent — sets, tuples, DataFrames, numpy scalars, datetimes — without crashing the run or losing type information?

## The sanitizer
**Path/Symbol:** `src/cuga/backend/cuga_graph/nodes/cuga_lite/executors/common/variable_utils.py` (`sanitize_value` :213-243, `_sanitize_recursive` :55-153, `_sanitize_set_element` :156-172, `hydrate_value` :199-210, `filter_new_variables` :294-327, `add_variables_to_manager` :413-468).
**Signature:** `sanitize_value(value) -> JSON-safe`; `hydrate_value(value) -> restored`; `filter_new_variables(all_locals, original_keys, always_include_keys=None) -> dict`.
**Data Shape:** envelope tags: `{__set_type__: "set"|"frozenset", items: [...], __cuga_enc__: true}`, `{__tuple_type__: "tuple", items: [...], __cuga_enc__: true}`, `{__pandas_type__: "DataFrame", records, columns, reconstruct}` / `{__pandas_type__: "Series", data, name, reconstruct}`.

### Decisive source
```python
# variable_utils.py:163-172 — unhashable-after-sanitize elements fall back to repr
def _sanitize_set_element(obj):
    if isinstance(obj, tuple):
        return {_TUPLE_TYPE_KEY: "tuple", "items": [...recursive...], _ENC_KEY: True}
    sanitized = VariableUtils._sanitize_recursive(obj)
    if isinstance(sanitized, (dict, list)):
        return repr(obj)   # keeps the SET constructible after JSON round-trip
    return sanitized

# variable_utils.py:134-137 — already-encoded envelopes pass through untouched
if VariableUtils._is_set_tag(obj) or VariableUtils._is_tuple_tag(obj):
    return obj   # ordinary user dicts with the same keys stay dicts (triple key check)
```

**Flow:** sanitize: numpy scalars → natives (nan/inf→None), ndarray → tolist+recurse; pandas NaT/NA→None, Timestamp→ISO, Timedelta→seconds; datetime/date/time→ISO; bytes→UTF-8 else base64; complex→{real,imag}; set/frozenset→tagged envelope with recursively-sanitized elements; DataFrame/Series→metadata envelope carrying a reconstruct hint. Hydrate: recognize envelopes by EXACT key-set match plus `__cuga_enc__ is True` and rebuild set/frozenset/tuple recursively; mappings/sequences recurse only when a child changed (identity preserved otherwise). `filter_new_variables`: diff against pre-execution keys ∪ always-include keys, skip `_`-prefixed, drop non-serializable with a debug log. `add_variables_to_manager` classifies created vs updated names and appends the summary header to the execution result.
**Invariant:** envelope recognition requires the FULL key-set match (`set(value.keys()) == {...}`) so a user's ordinary dict containing `__set_type__` is never mis-hydrated. Sanitization never raises — worst case an element degrades to `repr()`. The `__cuga_enc__` sentinel marks self-produced envelopes precisely so user data with colliding keys stays a plain dict.

**Probe:** direct tests `executors/tests/test_variable_creation_order.py::TestVariableCreationOrder` (creation-order LRU contract); `executors/tests/test_code_executor.py::test_variable_reordering` (:492), `::test_execution_with_variables` (:41); `tests/unit/test_variables_addendum_not_persisted.py` pins the variables-summary addendum stays out of persisted history.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "VariableUtils sanitize_value hydrate_value filter_new_variables _cuga_enc", limit: 10 });
```

## Verdict
Adopt tagged-envelope serialization for non-JSON types with exact-key-set recognition, repr-fallback over failure for unhashable set elements, and diff-based new-variable capture with underscore exclusion. Adapt the type coverage table (numpy/pandas/datetime) to your data plane. Omit the DataFrame reconstruct-hint strings unless your UI renders them.
