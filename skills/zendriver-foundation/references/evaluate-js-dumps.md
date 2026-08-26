<!-- capsule-v2 -->
# evaluate-js-dumps — the two JS-evaluation paths and the two-variant object dumper

**Source:** zendriver MIT `main@2c6d9c7daaab543d34e9fe2b0ef7eaa171c79760`; Codebase Memory `ext-zendriver`. **Question:** How does `evaluate` return complex objects, and how does `js_dumps` salvage objects that defeat JSON?

## evaluate: value vs deep serialization; js_dumps: two fallback scripts
**Path/Symbol:** `zendriver/core/tab.py:Tab.evaluate` (:737-769) and `js_dumps` (:771-943).
**Signature:** `async def evaluate(self, expression: str, await_promise=False, return_by_value=True)`; `async def js_dumps(self, obj_name: str, return_by_value=True)`.
**Data Shape:** `return_by_value=True` returns plain `.value`; `False` switches on `SerializationOptions(serialization="deep", max_depth=10, additional_parameters={"maxNodeDepth": 10, "includeShadowTree": "all"})` and returns `remote_object.deep_serialized_value.value`.

### Decisive source
```python
if errors:
    raise ProtocolException(errors)
if return_by_value:
    return remote_object.value
# deep_serialized_value is guaranteed to be present when
# serialization_options.serialization="deep"
return cast(DeepSerializedValue, remote_object.deep_serialized_value).value
```
and in `js_dumps`, the deliberate bypass (:916):
```python
# we're purposely not calling self.evaluate here to prevent infinite loop on certain expressions
remote_object, exception_details = await self.send(cdp.runtime.evaluate(js_code_a, ...))
if exception_details:
    # try second variant
    remote_object, exception_details = await self.send(cdp.runtime.evaluate(js_code_b, ...))
```

**Flow:** both send `runtime.evaluate` with `user_gesture=True` + `allow_unsafe_eval_blocked_by_csp=True`. `js_code_a` walks own+prototype keys (`Object.getOwnPropertyNames` up the prototype chain), depth-caps recursion at 2, stringifies functions, JSON-stringifies leftovers; if it *throws*, `js_code_b` runs a WeakSet-visited iterative copy skipping `enabledPlugin` and functions. Errors surface as `ProtocolException(exception_details)`.
**Invariant:** `js_dumps` is documented as not a source of truth (complex objects may not round-trip) and its result is a plain dict of key→best-effort-value; live probe confirmed `'x' in dump == False` for a page div — only enumerable/own properties appear. A port expecting DOM element identity from the dump will be wrong.
**Probe:** static anchor at pin: `grep -c 'we.re purposely not calling self.evaluate' zendriver/core/tab.py` → 1 (line 916); live-executed this pass: `js_dumps('document')` → dict without content keys; `evaluate('[1,2,3]', return_by_value=False)` → list via deep serialization.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-zendriver", query: "js_dumps dump object", limit: 5 });
```

## Verdict
Adopt the evaluate dual-return contract exactly (deep-serialization guarantee is version-sensitive); adapt the two dump scripts as templates for your own salvage heuristics; treat dumps as debugging output, never data.
