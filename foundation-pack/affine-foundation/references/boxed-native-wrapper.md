<!-- capsule-v2 -->
# Boxed — opt-out of deep Y conversion by wrapping raw values in a tagged Y.Map

**Source:** AFFiNE MIT `canary@b530198a3b5ec1fb9b9eb9b684e428ab9e387d5a`; Codebase Memory project `ext-affine`. **Question:** How can a value be stored in Yjs WITHOUT being recursively converted into Y types, yet still be reactive?

## Boxed
**Path/Symbol:** `blocksuite/framework/store/src/reactive/boxed.ts`: `Boxed` (:28-137), `Boxed.is` (:76-80), constructor (:107-131).
**Signature:** `new Boxed(value: T)` / `Boxed.from(map: Y.Map<T>)`; `getValue(): T`; `setValue(v): T`; static `is(x): x is Boxed`.
**Data Shape:** internal `Y.Map` with EXACTLY two keys: `type = '$blocksuite:internal:native$'` (NATIVE_UNIQ_IDENTIFIER, consts.ts :5) and `value = <raw value>`.

### Decisive source
```ts
static is = (value: unknown): value is Boxed =>
  value instanceof Y.Map && value.get('type') === NATIVE_UNIQ_IDENTIFIER;

constructor(value: Value) {
  if (value instanceof Y.Map && value.doc &&
      value.get('type') === NATIVE_UNIQ_IDENTIFIER) {
    this._map = value;                       // adopt existing remote map as-is
  } else {
    this._map = new Y.Map();
    this._map.set('type', NATIVE_UNIQ_IDENTIFIER as Value);
    this._map.set('value', value);           // RAW — no native2Y conversion
  }
  this._map.observeDeep(events => {
    events.forEach(event => {
      const isLocal = !event.transaction.origin || !this._map.doc ||
        event.transaction.origin instanceof Y.UndoManager ||
        event.transaction.origin.proxy ? true
        : event.transaction.origin === this._map.doc.clientID;
      this._onChange?.(this.getValue(), isLocal);
    });
  });
}
```

**Flow:** write path: `setValue` replaces the whole raw `value` entry (last-writer-wins, no merge inside the box). Read/conversion path: `native2Y(Boxed)` stores `boxed.yMap`, and `y2Native` reconstructs via `Boxed.from` when `Boxed.is(origin)` — so proxies treat the box atomically instead of recursing. Reactivity: observeDeep fires for ANY nested change when the raw value itself contains Y types the host mutated directly.

**Invariant:** (1) The `type` tag is the ONLY discriminator — a plain `{value: x}` Y.Map is NOT a Boxed; dropping or renaming the tag breaks round-trip detection. (2) Values inside a box are shared-by-reference until setValue: mutating `getValue()` in place does NOT notify peers unless the value contains live Y types. (3) The doc-bound adoption branch prevents double-wrapping a remote map (which would fork identity). (4) Functions/prototypes cannot survive storage — the wrapper stores data only (doc comment :12-13).

**Probe:** `blocksuite/framework/store/src/__tests__/yjs.unit.spec.ts` :131-164 'with native wrapper': pins `proxy.inner.native.getValue()` equality through the proxy, `setValue(['hello','world','foo'])` reaching the underlying stored map (`map.get('inner').get('native').get('value')`), and assigning a fresh Boxed through a proxy write.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-affine", query: "Boxed getValue setValue NATIVE_UNIQ_IDENTIFIER", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt tag-in-map atomic boxing for JSON-like payloads needing whole-value semantics; adapt tag constant; omit if deep CRDT merging of subfields is actually wanted.
