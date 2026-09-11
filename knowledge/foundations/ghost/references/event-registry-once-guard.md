<!-- capsule-v2 -->
# Webhook duplicate-registration guard — why does the event bus need hasRegisteredListener?

**Source:** Ghost MIT `main@81292b004cf59591f03d7dbe01f28f31c09ee813`; Codebase Memory `ext-ghost`. **Question:** What process-lifetime hazard does the named-listener registry solve that plain `events.on` does not?

## EventRegistry
**Path/Symbol:** `ghost/core/core/server/lib/common/events.js:EventRegistry` (:15–26).
**Signature:** `hasRegisteredListener(eventName: string, listenerName: string): boolean` over a subclassed EventEmitter; `setMaxListeners(100)`.
**Data Shape:** single process-wide instance exported; listeners must be NAMED functions to be findable.
### Decisive source
```js
class EventRegistry extends events.EventEmitter {
  hasRegisteredListener(eventName, listenerName) {
    return !!this.listeners(eventName).find((listener) => listener.name === listenerName);
  }
}
const eventRegistryInstance = new EventRegistry();
eventRegistryInstance.setMaxListeners(100);
```
**Flow (why it exists — in-source comment):** Ghost "reboots" inside long-lived test processes re-run boot wiring against the SAME module instance, so every reboot would stack another identical webhook listener → duplicate deliveries per event. The semi-hack matches by function NAME because closures can't be compared by identity across boot cycles.
**Invariant:** Any new model-event subscriber in this codebase must follow the same pattern: named handler + early-exit guard keyed on its name — otherwise webhook-style side effects multiply. The header comment is also an architectural warning: events coupling is deliberately NOT extracted into a shared package to avoid reinforcing it.
**Probe:** `grep -cF "hasRegisteredListener(eventName, listenerName)" ghost/core/core/server/lib/common/events.js` → expect `1`; `grep -cF "setMaxListeners(100)" ghost/core/core/server/lib/common/events.js` → expect `1`; direct test: `grep -cF "hasRegisteredListener" ghost/core/test/unit/server/lib/events.test.js` → expect `3` (the suite exercises the registry method and its once-only semantics).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ghost", query: "processWebhookTrigger registerListeners", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the named-listener once-guard for any rebootable-process test harness or multi-boot embedding. Adapt threshold (100) to host listener counts; omit the philosophical comment at your peril.
