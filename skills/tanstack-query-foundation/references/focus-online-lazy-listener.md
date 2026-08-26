<!-- capsule-v2 -->
# Focus/Online lazy environment listeners — how do global event sources stay free until first subscribe?

**Source:** TanStack Query MIT `main@bc423b37ef7fa2a34cfc7286945fd640d74b4071`; Codebase Memory `ext-ui-tanstack-query`. **Question:** How should singleton managers attach window listeners (visibilitychange / online / offline) only while someone actually cares?

## Subscribable onSubscribe/onUnsubscribe hooks
**Path/Symbol:** `packages/query-core/src/focusManager.ts:FocusManager` (:9–85), twin `onlineManager.ts:OnlineManager` (:6–70); base `subscribable.ts:Subscribable` (:1–30).
**Signature:** `class Subscribable<TListener> { subscribe(listener): () => void; hasListeners(): boolean; protected onSubscribe(); protected onUnsubscribe() }`.
**Data Shape:** `#focused?: boolean` (undefined = derive from document.visibilityState), `#cleanup?: () => void`, `#setup: SetupFn`.

### Decisive source
```ts
// Subscribable.subscribe — bound once in constructor:
this.subscribe = this.subscribe.bind(this)
subscribe(listener: TListener): () => void {
  this.listeners.add(listener)
  this.onSubscribe()
  return () => {
    this.listeners.delete(listener)
    this.onUnsubscribe()
  }
}

// FocusManager lazy lifecycle:
protected onSubscribe(): void {
  if (!this.#cleanup) {
    this.setEventListener(this.#setup)
  }
}
protected onUnsubscribe() {
  if (!this.hasListeners()) {
    this.#cleanup?.()
    this.#cleanup = undefined
  }
}
isFocused(): boolean {
  if (typeof this.#focused === 'boolean') return this.#focused
  return globalThis.document?.visibilityState !== 'hidden'
}
```

**Flow:** first subscribe installs the platform listener via #setup; each window event calls setFocused(focused?)/setOnline(bool) which CHANGE-DETECTS before notifying listeners; last unsubscribe tears down. setEventListener swaps setups safely (`#cleanup?.()` first) — tests inject fake setups to drive focus transitions without a real document.
**Invariant:** (1) the base class binds subscribe in the CONSTRUCTOR so passing the method reference unbound still works (useSyncExternalStore receives a stable function); (2) teardown runs exactly once, when listener size transitions to 0 — re-subscribing afterwards re-installs via onSubscribe because #cleanup was cleared; (3) undefined ≠ false for focus: undefined means "consult the document", so an explicit setFocused(undefined) RESETS to derived state rather than forcing unfocused; (4) notify loops use forEach over Set — listeners added during delivery don't fire this round.
**Probe:** `grep -n "visibilitychange" packages/query-core/src/focusManager.ts` (:23) and `grep -n "'online'" packages/query-core/src/onlineManager.ts | head -2`; direct tests `__tests__/focusManager.test.tsx`, `__tests__/onlineManager.test.tsx` drive fake setups.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ui-tanstack-query", name_pattern: "^FocusManager$|^Subscribable$", limit: 5 });
```

## Verdict
Adopt hook-based laziness for every ambient-event manager in a host app. Adapt setup fns per platform (React Native lacks addEventListener but keeps window). Omit nothing else. Note: both managers are exported singletons (`focusManager`, `onlineManager`) — ports wanting multiple instances must drop that.
