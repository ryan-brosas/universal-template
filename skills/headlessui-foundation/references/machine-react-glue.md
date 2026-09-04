<!-- capsule-v2 -->
# Machine + React glue — how does a framework-free reducer class notify React slices without tearing?

**Source:** Headless UI MIT `main@eea57cf46fd6767ed1059012f7073b88eb159fba`; Codebase Memory `ext-ui-headlessui`. **Question:** What are the exact send/subscribe semantics (shallowEqual slice gating, event-type listeners, SSR dispose) and the useSyncExternalStore bridge?

## Machine / shallowEqual / batch / useSlice
**Path/Symbol:** `packages/@headlessui-react/src/machine.ts:5-154`; bridge `react-glue.tsx:6-22` (`useSlice`).
**Signature:** `abstract class Machine<State, Event extends {type}>` with `subscribe<Slice>(selector, cb): () => void`, `on<T>(type, cb)`, `send(event)`; `batch<F>(setup: () => [callback, handle]): F`.
**Data Shape:** subscribers store `{ selector, callback, current }` — current slice cached for equality; private fields via `#state`/`#subscribers`.

### Decisive source
```ts
send(event) {
  let newState = this.reduce(this.#state, event)
  if (newState === this.#state) return            // identity short-circuit
  this.#state = newState
  for (let subscriber of this.#subscribers) {
    let slice = subscriber.selector(this.#state)
    if (shallowEqual(subscriber.current, slice)) continue   // slice-gated notify
    subscriber.current = slice
    subscriber.callback(slice)
  }
  for (let callback of this.#eventSubscribers.get(event.type)) callback(this.#state, event)
}
// shallowEqual covers arrays, Map/Set (entries), plain objects via Object.is per entry.
// batch(): run callback NOW, schedule handle in a microTask — coalesces N registerOption calls:
actions.registerOption = batch(() => { let options = []; let seen = new Set()
  return [ (id, dataRef) => { if (seen.has(dataRef)) return; seen.add(dataRef); options.push({id, dataRef}) },
           () => { seen.clear(); return this.send({ type: RegisterOptions, options: options.splice(0) }) } ]
})
// React side:
useSyncExternalStoreWithSelector(useEvent((onChange) => machine.subscribe(identity, onChange)),
                                 useEvent(() => machine.state), useEvent(() => machine.state),
                                 useEvent(selector), compare /* default shallowEqual */)
```

**Flow:** component actions call send() → reduce → identity check → per-subscriber selector recompute with shallowEqual gate → then fire event-type listeners (machines hook cross-machine reactions here, e.g. ListboxMachine closes on foreign stack Push). Server-side subscribe returns a no-op unsubscribing fn and the constructor self-disposes on next microtask. batch() gives register/unregister/goToOption their coalescing behavior across sibling renders.
**Invariant:** reducers MUST return the SAME reference for no-change or every subscriber re-runs; slice selectors may return tuples ([isTop, onStack]) which shallowEqual compares element-wise; event listeners receive state AFTER reduction; batched sends flush once per microtask with only the LAST payload for goToOption but ACCUMULATED payloads for register/unregister.
**Probe:** live `/tmp/hui-pass1-probe/probe-index-store.mjs` pins createStore void-action suppression + stateful notify (sibling primitive). Direct tests: listbox.test.tsx (124 its) exercises machine through public components incl. registration-heavy suites; graph probe resolves ListboxMachine.new/.reduce line-exact.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ui-headlessui", query: "useSlice shallowEqual", name_pattern: "^useSlice$|^shallowEqual$", limit: 5 });
```

## Verdict
Adopt the Machine class shape, identity short-circuit, and shallowEqual gate verbatim; adapt useSlice to your framework's external-store primitive (the wrapper exists solely to satisfy useSyncExternalStoreWithSelector's stable-fn requirements); omit batch() at your peril — option registration without it sends one action PER option mount and breaks the pendingFocus contract.
