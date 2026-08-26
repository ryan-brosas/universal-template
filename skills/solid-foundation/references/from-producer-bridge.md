<!-- capsule-v2 -->
# from() producer bridge — when does an external push source become a signal, and why equals:false?

**Source:** SolidJS solid MIT `main@f47845f9cc16ecbb316aa6560c7161f45af9a3d8`; Codebase Memory `solid`. **Question:** How do two producer shapes (subscribable vs setter-callback) collapse into one accessor, and what equality semantics result?

## Connected graph-selected seam
**Path/Symbol:** `packages/solid/src/reactive/observable.ts:from` (:87–106; overloads :91–92).
**Signature:** `from<T>(producer: Producer<T>, initialValue: T): Accessor<T>` / `from<T>(producer: Producer<T | undefined>): Accessor<T | undefined>` where `Producer` = `(setter: Setter<T>) => () => void` **or** `{ subscribe: (fn: (v:T)=>void) => (()=>void) | { unsubscribe(): void } }`.
**Data Shape:** discriminated by `"subscribe" in producer`; cleanup is normalized to "call or `.unsubscribe()`" at teardown time.

### Decisive source
```ts
const [s, set] = createSignal<T | undefined>(initalValue, { equals: false });
if ("subscribe" in producer) {
  const unsub = producer.subscribe(v => set(() => v));
  onCleanup(() => ("unsubscribe" in unsub ? unsub.unsubscribe() : unsub()));
} else {
  const clean = producer(set);          // producer drives the setter itself
  onCleanup(clean);
}
return s;
```

**Flow:** create `equals:false` signal → subscribable path: pass a `v => set(() => v)` sink into the producer's `subscribe`, keep the returned unsubscribable → callback path: hand the raw `Setter` to the producer, keep its cleanup fn → both register teardown via `onCleanup` under the current owner.
**Invariant:** `equals:false` means every pushed value notifies subscribers even if deep-equal — producer semantics, not value semantics (a plain `createSignal(initial)` would silently drop repeated pushes). Each `from()` call creates its OWN signal + subscription: no cross-consumer sharing, memoization, or refcounting. Initial value reaches readers only after the first push (or via the overload's `initialValue`).
**Probe:** `packages/solid/test/observable.spec.ts` "from subscribable" / "from producer" — both pin initial-value flow-through (`out()` reads `"Hi"` before any set) and live updates through the accessor.

## Get live surrounding code
**Retrieve:** the same executed BM25 retrieval ranks `reactive.observable.from` second (:93–106) directly under its sibling `subscribe`; server twin `server.reactive.from` also surfaces.
```ts
await mcp.codebase_memory.search_graph({ project: "solid", query: "observable from interop bridge subscribe", limit: 10 });
```

## Verdict
Adopt the two-form Producer union, the sink `v => set(() => v)`, and equals:false push semantics. Adapt naming (`initalValue` typo is upstream). Omit any assumption of subscription sharing — if you need fan-out from one source, wrap with your own shared memo; solid does not do it here. Caveat: server twin drops the `initialValue` overload entirely (see interop-server-twin-drift).
