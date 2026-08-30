<!-- capsule-v2 -->
# Webhook composition root — why is the dispatch pipeline assembled inside listen()?

**Source:** Ghost MIT `main@81292b004cf59591f03d7dbe01f28f31c09ee813`; Codebase Memory `ext-ghost`. **Question:** What boot-order constraint forces the serialize→payload→trigger chain to be built lazily?

## webhooks/index.js
**Path/Symbol:** `ghost/core/core/server/services/webhooks/index.js:listen` (:5–22).
**Signature:** `listen(): void`.
**Data Shape:** chain = `createSerialize({urlService}) → createPayload({serialize}) → new WebhookTrigger({models, payload, limitService})` → `registerListeners({events, trigger})`.
### Decisive source
```js
// Composition root for the webhook dispatch pipeline: builds the
// serialize → payload → trigger chain and registers the model-event
// listeners. Requires are deferred until listen() runs so the model layer
// isn't loaded before boot wires it.
module.exports = {
  listen() {
    const models = require('../../models');
    ...
    const serialize = createSerialize({ urlService });
    const payload = createPayload({ serialize });
    const trigger = new WebhookTrigger({ models, payload, limitService });
    registerListeners({ events, trigger });
  },
};
```
**Flow:** boot calls webhooks.listen() after models/url service are ready → factories close over their deps (testable without the singleton) → listeners registered once via the named-guard.
**Invariant:** Dependency INVERSION at module boundaries: each unit (serialize, payload, WebhookTrigger, registerListeners) receives its deps as plain factory args — only this root touches singletons. Requiring `../../models` at module top-level would load the Bookshelf registry before migrations/config are set during early boot. The trigger object itself carries no state besides injected deps — safe for the events bus to hold forever.
**Probe:** `grep -cF "const trigger = new WebhookTrigger({ models, payload, limitService });" ghost/core/core/server/services/webhooks/index.js` → expect `1`; `grep -cF "registerListeners({ events, trigger });" ghost/core/core/server/services/webhooks/index.js` → expect `1`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ghost", query: "WebhookTrigger constructor", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt lazy composition-root + factory-injected pipeline. Adapt module paths; keep models-required-inside-listen if your ORM has boot-order constraints.
