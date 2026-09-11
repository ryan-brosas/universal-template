<!-- capsule-v2 -->
# EventEmitter async-listener safety — what must a hand-rolled EventEmitter guarantee for async listeners?

**Source:** playwright Apache-2.0 `main@d4e1023f6c03a8dced50eb3db88c2217e7c1a86a`; Codebase Memory `ext-playwright`. **Question:** Why does Playwright fork Node's EventEmitter, and which behavioral guarantees must survive the port (single-listener fast path, mutation-during-emit, awaiting in-flight handlers)?

## Fork with pending-handler tracking and awaitable teardown
**Path/Symbol:** `packages/playwright-core/src/client/eventEmitter.ts:EventEmitter` (emit 64-82, `_callHandler` 84-100, `_addListener` 110-167, `removeListener` 185-233, `removeAllListeners` overloads 239-259).
**Signature:** `emit(type, ...args): boolean`; `removeAllListeners(type?, options?: { behavior?: 'wait'|'ignoreErrors'|'default' }): this | Promise<void>`.
**Data Shape:** `_events: Record<EventType, Listener | Listener[]>` where a SINGLE listener is stored bare (function) and only the second triggers an array; `_pendingHandlers: Map<EventType, Set<Promise<void>>>`.

### Decisive source
```ts
private _callHandler(type: EventType, handler: Listener, args: any[]): void {
    const promise = Reflect.apply(handler, this, args);
    if (!(promise instanceof Promise))
      return;
    let set = this._pendingHandlers.get(type);
    if (!set) {
      set = new Set();
      this._pendingHandlers.set(type, set);
    }
    set.add(promise);
    promise.catch(e => { ... }).finally(() => set.delete(promise));
}
...
// emit() — array path:
const len = handler.length;
const listeners = handler.slice();
for (let i = 0; i < len; ++i)
  this._callHandler(type, listeners[i], args);
```

**Flow:** emit looks up handlers; single-function fast path avoids allocation; array path iterates a **snapshot copy** so a listener that removes itself or others mid-emit cannot skip or double-call neighbors. Every returned Promise is tracked in the per-event pending set until settle; rejections go to `_rejectionHandler` when teardown installed one, else rethrow. `once()` uses a `OnceWrapper` whose wrapper function carries `.listener` so `removeListener(originalFn)` still finds and removes it (search matches wrapped via `wrappedListener`). The options-bearing `removeAllListeners` returns a Promise only when `{behavior:'wait'}` — it awaits ALL pending promises of that event (or every event) and throws the first collected error.
**Invariant:** Listener-count semantics stay Node-compatible (`listenerCount`, leak warning at maxListeners with `(existing as any).warned` latch); removing one of two listeners collapses the array back to a bare function (`if (list.length === 1) events[type] = list[0]`) — ports that always keep arrays break identity-based removal order expectations downstream. Emit is synchronous; async listener failures must never crash emit.
**Probe:** `grep -c "existing.length > m" packages/playwright-core/src/client/eventEmitter.ts` → `1`; `grep -c "promise instanceof Promise" packages/playwright-core/src/client/eventEmitter.ts` → `1`; `grep -c "list.length === 1" packages/playwright-core/src/client/eventEmitter.ts` → `1`; `grep -c "behavior === 'wait'" packages/playwright-core/src/client/eventEmitter.ts` → `1`; `grep -c "_pendingHandlers" packages/playwright-core/src/client/eventEmitter.ts` → `5`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-playwright", query: "_callHandler", limit: 10, fields: ["signature", "name", "file"] });
```
(CLI: `client.eventEmitter.EventEmitter._callHandler ... eventEmitter.ts 84-100`.)

## Verdict
Adopt the fork's three guarantees: snapshot iteration during emit, pending-promise accounting keyed by event, and awaitable/ignorable teardown. Adapt the leak-warning policy and OnceWrapper mechanics to your runtime's EventEmitter if you don't need byte-compatible behavior. Omit the `newListener`/`removeListener` meta-event re-emission subtleties unless your consumers rely on them (the port keeps them; note `events` is re-read after a `newListener` handler may have replaced `_events`). Direct unit coverage is internal-only at this commit — library tests exercise the emitter indirectly through every page/context event test (`tests/library/browsercontext-events.spec.ts`, 19 tests); keep grep pins as commit-scoped evidence.
