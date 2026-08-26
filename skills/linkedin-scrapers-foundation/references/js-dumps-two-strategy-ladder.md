<!-- capsule-v2 -->
# js_dumps — how do you export an arbitrary JS object (window, a JS app's state) into Python when return_by_value chokes or lies?

**Source:** zendriver AGPL-3.0 — PATTERNS ONLY. `main@2c6d9c7d`; Codebase Memory `ext-zendriver`. **Question:** how do you dump a complex live JS object with all its properties into a plain dict over CDP, given that `Runtime.evaluate` + `return_by_value` fails on non-JSON-able objects and silently drops prototype members?

## Two-strategy JS payload ladder + exception-triggered fallback
**Path/Symbol:** `zendriver/core/tab.py:js_dumps` (:771-943); the evaluate primitive it deliberately avoids is `Tab.evaluate` (:737-769).
**Signature:** `Tab.js_dumps(obj_name, return_by_value=True) -> Any` (dict) or `(RemoteObject|None, ExceptionDetails|None)` tuple when `return_by_value=False`.
**Data Shape:** strategy A (`___dumpY`): own+inherited property names via prototype-chain walk → per-key `___dump(obj[k], _d=0)` recursive dump capped at **depth 2**, values coerced primitives→raw / functions→`.toString()` / objects→recurse / else `JSON.stringify` then `.toString()`, skipping `obj[k] == window`; strategy B: IIFE with a `WeakSet` visited-set cycle guard, skipping `enabledPlugin` and ALL functions, recursing only into objects whose recursion yields keys.

### Decisive source
```python
# we're purposely not calling self.evaluate here to prevent infinite loop on certain expressions
remote_object, exception_details = await self.send(
    cdp.runtime.evaluate(js_code_a, await_promise=True,
                         return_by_value=return_by_value,
                         allow_unsafe_eval_blocked_by_csp=True))
if exception_details:
    # try second variant
    remote_object, exception_details = await self.send(cdp.runtime.evaluate(js_code_b, ...))
if exception_details:
    raise ProtocolException(exception_details)
```
```javascript
// strategy A key harvest: OWN + INHERITED via prototype chain
var [target, result] = [obj, []];
while (target !== null) {
    result = result.concat(Object.getOwnPropertyNames(target));
    target = Object.getPrototypeOf(target);
}
return Object.fromEntries(objKeys(obj).map(_ => [_, ___dump(obj[_])]))
// strategy B cycle guard + function skip
((obj, visited = new WeakSet()) => { if (visited.has(obj)) return {}; visited.add(obj); ... })()
```

**Flow:** "Dump window" or a SPA's state object breaks naive approaches three ways: (1) `return_by_value=True` raises for objects without a JSON-able representation; (2) `Object.keys` misses inherited members; (3) recursive dumps hit cycles and cross-realm windows. Strategy A walks the full prototype chain for names, dumps each value depth-capped at 2, and degrades every exotic value through functions→source text, unserializable→`JSON.stringify` fallback, still-failing→`.toString()`; it skips any value equal to `window` to avoid dumping the world into itself. If A throws (exception_details set), B runs instead: a WeakSet guards cycles, functions and `enabledPlugin` are skipped outright, and empty recursions are dropped. Only if BOTH fail does `ProtocolException` propagate to Python. The method intentionally bypasses `Tab.evaluate` (a comment pins this: calling it can infinite-loop on certain expressions), sending raw `runtime.evaluate` with `await_promise=True` and `allow_unsafe_eval_blocked_by_csp=True`.
**Invariant:** never trust a single serialization strategy for arbitrary JS — pair a greedy dumper with a defensive fallback keyed on EXCEPTION DETAILS, not on result inspection; cap recursion depth in the greedy one and rely on a visited-set in the defensive one; both must run with `allow_unsafe_eval_blocked_by_csp=True` because scraper pages routinely ship CSPs that block eval.
**Probe:** REAL tests pin the evaluate primitive this stands on — `tests/core/test_tab.py`: `test_evaluate_complex_object_no_error` (:470-481, deep-serialization of DOM nodes incl. body with complex refs), `test_evaluate_return_by_value_complex_object` (:484-498, asserts ProtocolException for `return_by_value=True` on complex object AND success with `return_by_value=False`), `test_evaluate_return_by_value_falsy` (:517-525, `0`/`[]`/`null` survive truthiness mangling), `test_evaluate_stress_test_complex_objects` (:528+, reference-chain stress matrix). `js_dumps` itself ships no direct unit test — coverage caveat recorded.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-zendriver", query: "js_dumps getOwnPropertyNames getPrototypeOf WeakSet ProtocolException", limit: 5 });
```

## Verdict
Adopt: two-payload exception-gated ladder + prototype-chain key harvest + depth-cap/visited-set split for exporting hostile JS state (feed counters, app state blobs) from any CDP session. Adapt depth caps and skip-lists to your target object. Omit strategy A's console.log debug noise. Coverage: source-pinned; evaluate primitive test-pinned, js_dumps itself has no upstream unit test (recorded caveat).
