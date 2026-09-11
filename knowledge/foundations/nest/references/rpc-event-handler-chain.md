<!-- capsule-v2 -->
# RPC event handler chain — how do duplicate-pattern event listeners fan out while message handlers overwrite?

**Source:** nest (MIT) `master@4c38a5ab100f`; Codebase Memory `nest`. **Question:** When two handlers register the same normalized pattern, what runs — and who composes multiple @EventPattern subscribers?

## Tail-appended linked list behind one Map entry
**Path/Symbol:** `packages/microservices/server/server.ts:Server.addHandler` (139-159); chain composition in `packages/microservices/listeners-controller.ts:ListenersController.forkJoinHandlersIfAttached` (192-207).
**Signature:** `addHandler(pattern: any, callback: MessageHandler, isEventHandler = false, extras: Record<string, any> = {})`.
**Data Shape:** `messageHandlers: Map<string /* normalized route */, MessageHandler>`; each handler may carry `.next` → forming a singly linked list; `isEventHandler`/`extras` are stamped onto the function object.

### Decisive source
```ts
const normalizedPattern = this.normalizePattern(pattern);
callback.isEventHandler = isEventHandler;
callback.extras = extras;
if (this.messageHandlers.has(normalizedPattern) && isEventHandler) {
  const headRef = this.messageHandlers.get(normalizedPattern)!;
  const getTail = (handler: MessageHandler) =>
    handler?.next ? getTail(handler.next) : handler;
  const tailRef = getTail(headRef);
  tailRef.next = callback;
} else {
  this.messageHandlers.set(normalizedPattern, callback);
}
// composition side (per registered event wrapper):
if (handlerRef.next) {
  const returnedValueWrapper = handlerRef.next(...(originalArgs as Parameters<MessageHandler>));
  return forkJoin({
    current: this.transformToObservable(currentReturnValue),
    next: this.transformToObservable(returnedValueWrapper),
  });
}
return currentReturnValue;
```

**Flow:** duplicate MESSAGE handler ⇒ Map overwrite (last wins). Duplicate EVENT handler ⇒ O(n) tail walk appends to the list. Dispatch only ever invokes the head (`handleEvent` → `handler(packet.data, context)`); each event *wrapper* closure created by ListenersController calls its own `.next` and `forkJoin`s the two results — recursion through wrappers composes the whole chain concurrently.
**Invariant:** first registration anchors the slot; every same-pattern event subscriber runs (fan-out), and no event listener is silently dropped; message semantics stay last-write-wins.
**Probe:** `packages/microservices/test/server/server.spec.ts` ('should find tail and assign a handler ref to it' — pre-seeds `head.next`, asserts after add `nextHandler.next === callback`).
**Runner caveat:** direct test execution blocked (deps uninstalled); expectation quoted from spec source.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nest", query: "addHandler event handler tail next", file_pattern: "packages/microservices/server/server.ts", limit: 6 });
// live @ pin: rank#1 Server.addHandler 139-159; also Server.getHandlerByPattern 165-170, Server.handleEvent 208-236
```

## Verdict
Adopt the map+linked-list registry and forkJoin fan-out composition; adapt the forkJoin result shape if your transport needs streamed partials instead of combined completion; omit GraphInspector entrypoint bookkeeping unless you port inspection too.
