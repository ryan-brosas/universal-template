<!-- capsule-v2 -->
# Webhook event registration ladder — how does dispatch subscribe to model events exactly once?

**Source:** Ghost MIT `main@81292b004cf59591f03d7dbe01f28f31c09ee813`; Codebase Memory `ext-ghost`. **Question:** How are webhook listeners wired to the model event bus without duplicate registration or firing during imports?

## registerListeners in listen.js
**Path/Symbol:** `ghost/core/core/server/services/webhooks/listen.js:registerListeners` (:43–63; event list :3–38).
**Signature:** `registerListeners({ events, trigger }): void`.
**Data Shape:** 29 events declared (count lines matching `^\s*'`): site.changed; post/page × {added, deleted, edited, published, published.edited, unpublished, scheduled, unscheduled, rescheduled}; tag × {added, edited, deleted}; member × {added, deleted, edited}; post/page tag attached/detached.
### Decisive source
```js
_.each(WEBHOOKS, (event) => {
  // @NOTE: The early exit makes sure the listeners are only registered once.
  if (events.hasRegisteredListener(event, 'processWebhookTrigger')) {
    return;
  }
  events.on(event, function processWebhookTrigger(model, options) {
    // CASE: avoid triggering webhooks when importing
    if (options && options.importing) {
      return;
    }
    trigger.trigger(event, model);
  });
});
```
**Flow:** for each declared event: idempotency guard by NAMED listener function → register → on fire: skip when `options.importing` → fire-and-forget trigger.
**Invariant:** The listener is a NAMED function expression and the guard matches by `listener.name` (`EventRegistry.hasRegisteredListener`, lib/common/events.js :19–23) — renaming the inner function silently breaks once-only registration across Ghost reboots in tests. Import suppression is per-call via options, not a global mute. `trigger.trigger` is deliberately not awaited — delivery must never block or reject into the model save path.
**Probe:** `grep -cF "hasRegisteredListener(event, 'processWebhookTrigger')" ghost/core/core/server/services/webhooks/listen.js` → expect `1`; `grep -cF "options.importing" ghost/core/core/server/services/webhooks/listen.js` → expect `1`; `grep -c "^\s*'" ghost/core/core/server/services/webhooks/listen.js` → expect `29`; direct test: `grep -cF "it('has registered listener'" ghost/core/test/unit/server/lib/events.test.js 2>/dev/null` may be absent — anchor instead on `hasRegisteredListener(eventName, listenerName)` in `ghost/core/core/server/lib/common/events.js` → expect `1`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ghost", query: "processWebhookTrigger registerListeners", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt named-listener idempotent registration + import suppression + unawaited dispatch. Adapt the event vocabulary to host models; omit lodash iteration.
