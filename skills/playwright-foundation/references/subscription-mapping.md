<!-- capsule-v2 -->
# Event-to-subscription mapping — when do protocol events actually get subscribed on the wire?

**Source:** playwright Apache-2.0 `main@d4e1023f6c03a8dced50eb3db88c2217e7c1a86a`; Codebase Memory `ext-playwright`. **Question:** How do I avoid flooding the peer with high-frequency events (console, network, socket frames) that nobody is listening for — and when exactly do subscriptions flip on and off?

## First listener enables; last removal disables
**Path/Symbol:** `packages/playwright-core/src/client/channelOwner.ts:ChannelOwner.on/off` (78-111) + `_updateSubscription` (72-76) + `_setEventToSubscriptionMapping`.
**Signature:** `on(event, listener): this`; `off(event, listener): this`; mapping: `Map<clientEventName, protocolEventName>`; wire call `(this._channel as any).updateSubscription({ event: protocolEvent, enabled })`.
**Data Shape:** client event names (e.g. `'console'`) map to protocol event names via a per-class table installed by subclasses (`_setEventToSubscriptionMapping`); unmapped events are purely local and never touch the wire.

### Decisive source
```ts
private _updateSubscription(event: string | symbol, enabled: boolean) {
    const protocolEvent = this._eventToSubscriptionMapping.get(String(event));
    if (protocolEvent)
      (this._channel as any).updateSubscription({ event: protocolEvent, enabled }).catch(() => {});
}

override on(event: string | symbol, listener: Listener): this {
    if (!this.listenerCount(event))
      this._updateSubscription(event, true);
    super.on(event, listener);
    return this;
}
...
override off(event: string | symbol, listener: Listener): this {
    super.off(event, listener);
    if (!this.listenerCount(event))
      this._updateSubscription(event, false);
    return this;
}
```

**Flow:** every mutating listener method (`on`, `addListener`, `prependListener`) checks `listenerCount === 0` BEFORE adding — zero means this is the first, so enable the mapped protocol event. Every removing method re-checks AFTER removal — zero means last one left, disable. The updateSubscription round-trip is fire-and-forget with a swallowed rejection: subscription state must never reject user code or block add/remove.
**Invariant:** Enable/disable decisions are made on COUNT, not identity — adding two listeners then removing one keeps the subscription live; the enable message precedes the listener registration in program order so no early events are missed by an already-registered listener. Unmapped events stay local-only.
**Probe:** `grep -c "listenerCount(event))" packages/playwright-core/src/client/channelOwner.ts` → `5` (on/addListener/prependListener enable + off/removeListener disable); `grep -c "updateSubscription({ event: protocolEvent, enabled })" packages/playwright-core/src/client/channelOwner.ts` → `1`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-playwright", query: "_updateSubscription", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt count-gated lazy subscription with fire-and-forget wire updates. Adapt which events are subscription-gated (map only the expensive ones) and your transport's subscribe message shape. Omit the protocol-name indirection if your client/protocol names already match 1:1. Direct behavior pinned by network/socket event tests in the library suite (`tests/library/browsercontext-events.spec.ts` family); the count-gating itself has no dedicated unit test at this commit — keep the grep pins plus a manual double-listener check in your port's test battery.
