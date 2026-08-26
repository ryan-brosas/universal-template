<!-- capsule-v2 -->
# JS evaluation layer — how do you round-trip unserializable values and recover from illegal top-level `return`?

**Source:** browser-harness MIT `main@41108b8676d4bdb58b26ab3b079c0b7b0f8f3926`; Codebase Memory `browser-harness`. **Question:** `Runtime.evaluate` returns values that aren't valid JSON (NaN/Infinity/BigInt) and rejects bare `return` at top level — how does a helper normalize both?

## unserializable decode + exception detail surfacing + return-wrapper retry
**Path/Symbol:** `src/browser_harness/helpers.py:_decode_unserializable_js_value` (:80-91), `_runtime_value` (:94-110), `_runtime_evaluate` (:113-118), `js` (:460-474).
**Signature:** `js(expression, target_id=None)`; `_runtime_evaluate(expression, session_id=None, await_promise=False)`.
**Data Shape:** CDP `result` may carry `value` (JSON) OR `unserializableValue` (string like `"NaN"`, `"Infinity"`, `"-0"`, `"123n"`); `exceptionDetails` carries line/column/description.

### Decisive source
```python
def _decode_unserializable_js_value(value):
    if value == "NaN": return math.nan
    if value == "Infinity": return math.inf
    if value == "-Infinity": return -math.inf
    if value == "-0": return -0.0
    if value.endswith("n"): return int(value[:-1])      # BigInt literal
    return value

def js(expression, target_id=None):
    sid = cdp("Target.attachToTarget", targetId=target_id, flatten=True)["sessionId"] if target_id else None
    try:
        return _runtime_evaluate(expression, session_id=sid, await_promise=True)
    except RuntimeError as e:
        if _is_illegal_return_error(e):                 # "Illegal return statement"
            return _runtime_evaluate(_wrap_js_function(expression), session_id=sid, await_promise=True)
        raise
```
`_wrap_js_function` = `f"(function(){{{expression}}})()"`. `_runtime_value` raises a RuntimeError carrying line/col + a 160-char expression snippet on `exceptionDetails` or `subtype=="error"`.

**Flow:** evaluate as-is with `returnByValue=True, awaitPromise=True` → decode `value`/`unserializableValue` → on exception raise with location+snippet → on "Illegal return statement" retry inside a function wrapper.
**Invariant:** the retry must be triggered ONLY by the illegal-return error — wrapping unconditionally would mis-wrap nested functions that contain their own returns; exception messages are actionable (location + truncated expression), never bare.
**Probe:** `tests/unit/test_helpers.py:56` `test_page_info_raises_clear_error_on_js_exception` pins the exception-surfacing path.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "browser-harness", query: "unserializableValue NaN BigInt js wrapper return", limit: 10, fields: ["name","file","lines"] });
```

## Verdict
Adopt the decode table + conditional wrapper-retry + location-bearing errors for any CDP/JS bridge; adapt the snippet limit; omit nothing. Exception path is test-pinned.
