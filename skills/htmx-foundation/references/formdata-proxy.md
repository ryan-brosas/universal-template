<!-- capsule-v2 -->
# FormData proxy — how do `htmx.values()` results behave like objects while staying live-backed by FormData?

**Source:** htmx MIT `master@ad56dff71e55d9c717447437b4c942a64575d4b2` (v2.0.10); Codebase Memory `ext-htmx`. **Question:** What proxy traps must a porter implement so `values.k`, array mutation, `Object.assign`, `JSON.stringify`, and symbol reads all work against one FormData?

## formDataProxy: get/set/deleteProperty/ownKeys over a real FormData
**Path/Symbol:** `src/htmx.js:formDataProxy` (:4193-4258) + `formDataArrayProxy` (:4154-4187) + `toJSON` branch (:4208-4211).
**Signature:** `function formDataProxy(formData)` → Proxy wrapping the FormData; `function formDataArrayProxy(formData, name, array)` → Proxy wrapping the value array for multi-entry keys.
**Data Shape:** Get semantics: 0 entries ⇒ `undefined` (retro-compat with the old plain-object API), 1 entry ⇒ scalar, ≥2 ⇒ array proxy. Set: `delete(name)` then append — arrays via forEach-append, plain objects JSON-stringified EXCEPT Blobs, scalars appended raw. Symbol gets forward to Reflect with `.apply(formData, ...)` rebinding to dodge illegal-invocation errors.

### Decisive source
```js
if (name === 'toJSON') { return () => Object.fromEntries(formData) }
...
const array = formData.getAll(name)
if (array.length === 0) { return undefined }
else if (array.length === 1) { return array[0] }
else { return formDataArrayProxy(target, name, array) }
...
set: function(target, name, value) {
  if (typeof name !== 'string') { return false }
  target.delete(name)
  if (value && typeof value.forEach === 'function') { value.forEach(v => target.append(name, v)) }
  else if (typeof value === 'object' && !(value instanceof Blob)) { target.append(name, JSON.stringify(value)) }
  else { target.append(name, value) }
  return true
},
ownKeys: function(target) { return Reflect.ownKeys(Object.fromEntries(target)) },
getOwnPropertyDescriptor: function(target, prop) { return Reflect.getOwnPropertyDescriptor(Object.fromEntries(target), prop) }
```

Array-proxy mutation contract: numeric/length/function-property reads pass through; `push` appends to BOTH array and FormData; any method call or index write rewrites the WHOLE key (`delete(name)` + re-append of every element) — single-element arrays read back as the bare scalar.
**Flow:** every `htmx.values()` / `requestConfig.parameters` consumer touches this proxy; mutations are immediately visible to the wire encoder because there is only one source of truth.
**Invariant:** `JSON.stringify(proxy)` works through the `toJSON` trap returning `Object.fromEntries`; `Object.assign({}, proxy)` works through ownKeys+getOwnPropertyDescriptor (both rebuilt from `Object.fromEntries` each call). `Symbol.toStringTag` forwards to the real FormData so `vals[Symbol.toStringTag] === 'FormData'`, and symbol SETS are rejected (typeof name !== 'string' ⇒ false) — the type brand cannot be spoofed.

**Probe:** Direct test `test/core/api.js:587` "tests for formDataProxy array updating and testing for loc coverage": `vals.do.push('test')` grows the FormData entry set; `vals.do = ['bob','jim']` replaces it; `arr[0]='override'` index-write rewrites; symbol-brand asserts at :605-609. Object-shape pin "JSON.stringify(apiValues)" at :582. Executed headless: single→scalar, delete removes key, set replaces, multi reads as array with [0] access.

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-htmx", query: "formDataProxy values proxy FormData", limit: 4 });
```
(rank-1 `src.htmx.formDataProxy src/htmx.js 4193-4258`)

## Verdict
Adopt the trap matrix verbatim — each branch exists because a test or real consumer (URL encoders, event detail inspectors) needed it. Adapt the Blob exemption if your host lacks Blob. Omit the 0-entry `undefined` retro-compat ONLY for a greenfield API where `''`-or-null semantics are acceptable; existing htmx behaviors depend on falsy-for-absent.
