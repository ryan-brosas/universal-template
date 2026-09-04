<!-- capsule-v2 -->
# Zones over AsyncLocalStorage — how does call metadata cross awaits without leaking into server events?

**Source:** playwright Apache-2.0 `main@d4e1023f6c03a8dced50eb3db88c2217e7c1a86a`; Codebase Memory `ext-playwright`. **Question:** How do I carry per-API-call context (name, stack, reported-flag) across arbitrary await chains — and keep it OFF unrelated work triggered from the same call site (like inbound event dispatch)?

## Immutable zone chain; outbound messages run under emptyZone
**Path/Symbol:** `packages/utils/zones.ts:Zone` (23-55) + consumers `client/connection.ts:206` (`emptyZone.run` on send) and `client/waiter.ts:40` (`currentZone().without('apiZone')`).
**Signature:** `zone.with(type, data): Zone`; `zone.without(type?): Zone`; `zone.run<R>(func): R`; `currentZone(): Zone` (falls back to `emptyZone` singleton).
**Data Shape:** `ZoneType = 'apiZone' | 'stepZone'`; store is an immutable `ReadonlyMap` copied per `with()`/`without()`; the AsyncLocalStorage instance is module-private so zones can only be entered via `run`.

### Decisive source
```ts
with(type: ZoneType, data: unknown): Zone {
    return new Zone(this._asyncLocalStorage, new Map(this._data).set(type, data));
}
...
// connection.ts — sending to the server:
// We need to exit zones before calling into the server, otherwise
// when we receive events from the server, we would be in an API zone.
emptyZone.run(() => this.onmessage({ ...message, metadata }));
```

**Flow:** `_wrapApiCall` creates a fresh apiZone and enters it with `currentZone().with('apiZone', apiZone).run(...)`; any code awaiting inside sees it via `currentZone().data('apiZone')`. Two deliberate exits exist: (1) **outbound sends run under `emptyZone`** so that when the server's reply/event handlers fire synchronously off this send they do not inherit the caller's zone; (2) **Waiters snapshot `currentZone().without('apiZone')` at construction** so event callbacks executing much later (e.g. predicate evaluation) don't mistake themselves for part of the original API call.
**Invariant:** Zones are immutable values — `with` never mutates the parent; crossing into the transport layer must clear context or you get cross-talk (event handlers reporting as API steps); long-lived listeners must capture a *stripped* zone, never the live one.
**Probe:** `grep -c "emptyZone.run" packages/playwright-core/src/client/connection.ts` → `2` (send + abort paths); `grep -c "without('apiZone')" packages/playwright-core/src/client/waiter.ts` → `1`; `grep -c "_savedZone" packages/playwright-core/src/client/waiter.ts` → `4`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-playwright", query: "Zone without emptyZone", limit: 10, fields: ["signature", "name", "file"] });
```
(CLI: returns `packages.utils.zones.Zone.without ... zones.ts 36-40`.)

## Verdict
Adopt immutable-zone context propagation plus the two exit rules (transport boundary + listener snapshot). Adapt the storage backend if your runtime lacks AsyncLocalStorage (e.g. web: a module-level current-zone variable with explicit save/restore), and rename zone types for your domain. Omit `'stepZone'` unless porting the test-runner step plane. Direct unit tests for Zone are internal-only at this commit; behavior is pinned through Waiter/page tests (`tests/library/browsercontext-events.spec.ts`) — verify your port's no-leak property with an assertion inside a fake event handler.
