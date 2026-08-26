<!-- capsule-v2 -->
# IPC result sanitization — cleanJson round-trip that survives Electron structured clone

**Source:** bruno MIT `main@675965612ff11b23bc9b6c9541110a287bcb2967`; Codebase Memory `ext-bruno`. **Question:** Why does sending script-produced values (`bru.setVar("a", {b:3})`-style objects, Errors, typed arrays) from main to renderer crash with "Failed to serialize arguments", and what is the minimal fix?

## Connected graph-selected seam
**Path/Symbol:** `packages/bruno-js/src/utils.js:cleanJson` (:144-227), `cleanCircularJson` (:229+).
**Signature:** `cleanJson(data) → data'` (JSON.parse(JSON.stringify(data, replacer), reviver)); failure returns the ORIGINAL data.
**Data Shape:** replacer handles three classes: circular refs → `'[Circular Reference]'`; Error-like objects (instanceof OR duck-typed cross-realm via `[object Error]` + message/stack check) → plain object with name/message + own props; typed arrays (12 baseline kinds incl. Float16Array when present) → `{__cleanJSONType: <name>, __cleanJSONValue: Buffer.from(buffer).toJSON()}`. Reviver reverses the typed-array envelope by name lookup.

### Decisive source
```js
// Objects that are created inside developer mode execution context result in an
// serialization error when sent to the renderer process ... How to reproduce:
// Remove the cleanJson fix and execute: bru.setVar("a", {b:3});
const seen = new WeakSet();
const replacer = (key, value) => {
  if (typeof value === 'object' && value !== null) {
    if (seen.has(value)) return '[Circular Reference]';
    seen.add(value);
    // instanceof + [[Class]] cover same-realm; duck-type fallback for cross-realm/cross-context
    if (value instanceof Error || Object.prototype.toString.call(value) === '[object Error]' || ...) { ... }
```

**Flow:** stringify with WeakSet cycle detection → error normalization (name/message live on the prototype; own-property copy pulls stack etc.) → binary envelope for typed arrays → parse back with reviver reconstructing real typed-array instances from the envelope. Whole thing wrapped in try/catch returning the input unchanged on any failure — sanitization must never be the thing that breaks a request.
**Invariant:** the VM sandbox creates objects in a DIFFERENT realm, so `instanceof Error` alone misses them — the duck-typed fallback is required, not decorative; reviver must verify BOTH envelope keys before reconstructing; Buffer.from(value.buffer) assumes full-view arrays (byteOffset/length edge cases accepted upstream).
**Probe:** no dedicated utils spec for cleanJson in bruno-js/tests (utils.spec covers interpolation only) — coverage caveat recorded; exercised indirectly through scripting runtime tests.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-bruno", query: "cleanJson cleanCircularJson", limit: 5 });
```

## Verdict
Adopt the three-class replacer + realm-safe error duck-typing + fail-open wrapper. Adapt the envelope keys/binary handling to your transport (or use a structured-clone-safe format); omit Bruno's Float16 special-casing if your floor excludes it. Coverage caveat: no direct unit spec file.
