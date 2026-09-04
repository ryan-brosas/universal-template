<!-- capsule-v2 -->
# createYProxy — native↔Y bridge with loop-breaking origin tags and WeakMap proxy registry

**Source:** AFFiNE MIT `canary@b530198a3b5ec1fb9b9eb9b684e428ab9e387d5a`; Codebase Memory project `ext-affine`. **Question:** How do plain JS objects stay transparently two-way-bound to Y types without observer feedback loops, and which array methods must be special-cased?

## createYProxy / ReactiveYArray / ReactiveYMap / BaseReactiveYData
**Path/Symbol:** `blocksuite/framework/store/src/reactive/proxy.ts`: `createYProxy` (:352-390), `ReactiveYArray._getProxy` (:45-194), `ReactiveYMap._getProxy` (:244-324); `base-reactive-data.ts`: `_onObserve` (:24-43), `_transact` (:55-57).
**Signature:** `createYProxy<T>(yAbstract: unknown, options?: ProxyOptions<T>): T`; every proxy mutation routes through `this._transact(doc, fn)` which tags the transaction `{ doc, proxy: true, target }`.
**Data Shape:** `proxies = new WeakMap<YType, BaseReactiveYData>` registry (memory.ts); `_skipNext` boolean latch; `_stashed` per-index/key set; Text and Boxed wrappers carry their own bind(onChange).

### Decisive source
```ts
// base-reactive-data._onObserve — WHICH remote/self events trigger a model refresh
if (
  event.transaction.origin?.force === true ||
  (event.transaction.origin?.proxy !== true &&          // skip OUR OWN writes
    (!event.transaction.local ||                         // remote peer write
      event.transaction.origin instanceof Y.UndoManager)) // undo/redo re-entry
) { handler(); }
```
```ts
// splice is intercepted because default Array.prototype.splice would bypass Y
if (p === 'splice') {
  return (start, deleteCount?, ...items) => {
    ...
    this._transact(doc, () => {
      this._ySource.delete(start, count);
      this._ySource.insert(start, yItems);
    });
    const result = Array.prototype.splice.apply(target, [start, count,
      ...yItems.map(yItem => createYProxy(yItem, this._options))]);
    return result;
  };
}
// shift/unshift get the same treatment (:120-157)
```

**Flow:** read path: y2Native walks Y types producing plain objects, and `transform` swaps in Reactive proxies for Y.Map/Y.Array/Y.Text/Boxed nodes (memoized by the WeakMap so identity is stable). Write path: proxy trap → `native2Y(value)` → `_transact(doc, ...)` tagged `{proxy:true}` → Y fires event → observer sees `origin.proxy === true` and skips the model refresh. Remote updates (origin ≠ proxy-tagged, or local non-proxy) run the handler under `_updateWithSkip`, which sets `_skipNext` so the resulting local mirror write doesn't bounce back into Y.

**Invariant:** (1) The `proxy: true` origin tag IS the loop-breaker — any write path that forgets the tag causes an infinite observe→write cycle on first mutation. (2) Only `splice/shift/unshift/push-by-index/delete` are bridged for arrays; other Array methods silently operate on the mirror only — extending coverage is the porter's job. (3) `proxies.get(this._ySource)` MUST exist before mutation ("YData is not subscribed before changes" guard :69-75,:266-271) — creating raw references to underlying Y types bypasses the registry and corrupts state.

**Probe:** `blocksuite/framework/store/src/__tests__/yjs.unit.spec.ts` :10-68 pins push/splice/index-set/shift/unshift mirroring both ways (`proxy.splice(1,1)` ⇒ `arr.toJSON()` updated); :72-115 pins deep object writes reaching nested Y.Maps.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-affine", query: "createYProxy ReactiveYArray ReactiveYMap _onObserve _updateWithSkip", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the origin-tag + WeakMap + method-interception trio wholesale; adapt wrapper types (Text/Boxed) to host rich-value needs; omit at your peril — this is the loop-safety kernel.
