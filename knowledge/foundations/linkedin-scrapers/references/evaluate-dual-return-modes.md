<!-- capsule-v2 -->
# Tab.evaluate dual-return contract — when must you flip `return_by_value=False`, and what does each branch actually hand back?

**Source:** zendriver AGPL-3.0 — PATTERNS ONLY. `main@2c6d9c7d`; Codebase Memory `ext-zendriver`. **Question:** one method serves both "give me plain JSON-able data" and "serialize this hostile object graph anyway" — where exactly does the mode split live, what flags ride along, and which documented return type is a lie?

## two serialization modes inside ONE Runtime.evaluate call
**Path/Symbol:** `zendriver/core/tab.py:Tab.evaluate` (:737-769); `cdp.runtime.SerializationOptions` (`zendriver/cdp/runtime.py:32-51`); `cdp.runtime.DeepSerializedValue` (`zendriver/cdp/runtime.py:70-108`); deliberate non-caller contrast `Tab.js_dumps` (:916-942, bypass comment :933).
**Signature:** `async def evaluate(expression: str, await_promise: bool = False, return_by_value: bool = True) -> Any | None | Tuple[RemoteObject, ExceptionDetails | None]` — the `Tuple[...]` arm of that hint is **DEAD CODE**: no path returns it (the tuple return belongs to `js_dumps`, :939-942).
**Data Shape:** by-value branch returns `remote_object.value` — whatever survived JSON round-tripping (primitives, plain arrays/objects; `None` for undefined). Deep branch builds `SerializationOptions(serialization="deep", max_depth=10, additional_parameters={"maxNodeDepth": 10, "includeShadowTree": "all"})` and returns `remote_object.deep_serialized_value.value`. `DeepSerializedValue` carries `type_` + optional `value`/`object_id`/`weak_local_object_reference`; per CDP docs on that last field: when a reference is met more than once, the value is provided ONLY to one of the serialized occurrences (dedup-by-reference, unique per CDP call).

### Decisive source
```python
ser: cdp.runtime.SerializationOptions | None = None          # :744
if not return_by_value:                                       # deep mode ONLY here
    ser = cdp.runtime.SerializationOptions(
        serialization="deep",                                 # :747
        max_depth=10,
        additional_parameters={"maxNodeDepth": 10, "includeShadowTree": "all"},
    )

remote_object, errors = await self.send(
    cdp.runtime.evaluate(
        expression=expression,
        user_gesture=True,                                    # :755 — fixed, both modes
        await_promise=await_promise,
        return_by_value=return_by_value,
        allow_unsafe_eval_blocked_by_csp=True,                # :758 — fixed, both modes
        serialization_options=ser,
    )
)
if errors:
    raise ProtocolException(errors)                           # :763 — same error contract
                                                              #   as capture-family sends
if return_by_value:
    return remote_object.value                                # :766
# serialization_options.serialization="deep"
return cast(DeepSerializedValue, remote_object.deep_serialized_value).value   # :769
```

**Flow:** ONE `Runtime.evaluate` send, then branch on the flag. By-value: Chrome JSON-serializes the result; anything non-JSON-able (functions, DOM nodes, cyclic graphs) degrades or throws inside the browser — you get `None`/partial shapes, not an error you can catch in Python. Deep mode: `SerializationOptions` **overrides** `generatePreview` AND `returnByValue` (per its docstring), walks the object graph to `max_depth=10` V8 levels and `maxNodeDepth=10` DOM levels, serializes open+closed shadow trees (`includeShadowTree:"all"`), and hands back typed `DeepSerializedValue` nodes — so cyclic/DOM-attached structures survive truncation instead of exploding. Both branches share fixed `user_gesture=True` (expressions run as if user-initiated) and `allow_unsafe_eval_blocked_by_csp=True` (evaluation works on CSP-hardened pages); both raise `ProtocolException(errors)` on exception details — identical error contract to the page-capture family. The sibling `js_dumps` does NOT route through this method on purpose ("we're purposely not calling self.evaluate to prevent infinite loop on certain expressions", :933) and its own `return_by_value=False` path returns the raw `(remote_object, exception_details)` tuple with a recorded upstream TODO ("Why not remote_object.deep_serialized_value.value?", :940) — so the two methods' False-mode returns are DIFFERENT SHAPES by design; porters must not unify them.
**Invariant:** (1) never branch on the hinted tuple — `evaluate` ALWAYS raises-or-returns-a-value; the tuple arm exists only in `js_dumps`; (2) flipping to `return_by_value=False` is THE remedy when by-value returns `None`/mangled data on DOM nodes or cyclic graphs — but deep ≠ unlimited: depth caps at 10/10 and cycles truncate rather than error; (3) `user_gesture=True` + CSP-bypass are baked in — do not re-add them at call sites and do not assume expressions respect CSP; (4) repeated object references deep-serialize ONCE (`weak_local_object_reference`) — reconstruction needs reference-following, not repeated inline values; (5) the `body:not(.no-js)` trick in the direct test doubles as a JS-ran assertion — reusable gate before trusting any evaluate result.
**Probe:** real upstream test `tests/core/test_tab.py::test_evaluate_complex_object_no_error` (:470-477): loads `tests/sample_data/complex_object.html` (a fixture that DELIBERATELY attaches `document.body.complexRef = document`, `structure.self = structure`, 100-level nested chains, and per-element circular next/prev rings), then `await tab.evaluate("document.querySelector('body:not(.no-js)')", return_by_value=False)` asserting a non-None deep-serialized node — i.e., the exact graph that breaks by-value round-trips. By-value usage pinned throughout `tests/core/test_react_controlled_input.py` (`tab.evaluate("document.getElementById('state-value').textContent") == "10"` :33-35). Deterministic anchors: `grep -n 'serialization="deep"' zendriver/core/tab.py` → :747; `grep -n 'maxNodeDepth' zendriver/core/tab.py` → :749; `grep -n 'user_gesture=True' zendriver/core/tab.py` → :755; `grep -n 'deep_serialized_value' zendriver/core/tab.py` → :769; `grep -n 'purposely not calling self.evaluate' zendriver/core/tab.py` → :933. Graph probes resolve `Tab.evaluate Method 737-769` and `DeepSerializedValue Class 70-108`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-zendriver", query: "evaluate SerializationOptions DeepSerializedValue return_by_value await_promise", limit: 6 });
```

## Verdict
Adopt: single-send dual-mode evaluate with the mode split expressed purely through `SerializationOptions` presence; fixed trusted+CSP-bypass flags; `ProtocolException` error contract; by-value for plain data, deep (`return_by_value=False`, caps 10/10, shadow trees all) for DOM/cyclic graphs. Patterns only (AGPL) — reimplement the contract, never the code. Pairs with `js-dumps-two-strategy-ladder` (prototype-chain harvest that bypasses this method) and `page-capture-download-gate` (shared ProtocolException skeleton).
