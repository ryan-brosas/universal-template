<!-- capsule-v2 -->
# Webhook dual-serialization payload — how does one payload carry both current and previous state?

**Source:** Ghost MIT `main@81292b004cf59591f03d7dbe01f28f31c09ee813`; Codebase Memory `ext-ghost`. **Question:** How is the `{post: {current, previous}}` webhook shape produced, and why must relation loading be surgical?

## serialize(event, model) factory
**Path/Symbol:** `ghost/core/core/server/services/webhooks/serialize.js:serialize` (:27–108; relation loader :17–23; key map :10–15).
**Signature:** `({ urlService }) => async (event, model): Promise<{ [singular]: { current, previous } }>` — resource name derived via `event.match(/(\w+)\./)[1]` + `s` (:32–33).
**Data Shape:** posts/pages get `formats: ['html','plaintext']` + `withRelated: ['tags','authors']`; members get `load(['labels','products','newsletters'])`. `_changed` keys are MODEL-level; API serialization renames some (`members`: products→tiers, stripeSubscriptions→subscriptions).
### Decisive source
```js
const SERIALIZED_KEYS = { members: { products: 'tiers', stripeSubscriptions: 'subscriptions' } };
const loadRequiredUrlRelations = async (model, urlService) => {
  const required = urlService.getRequiredRelations();
  const missing = required.filter((relation) => !model.relations[relation]);
  if (missing.length) { await model.load(missing); }
};
...
previous = _.pick(frame.response[docName][0], changed.map((key) => SERIALIZED_KEYS[docName]?.[key] ?? key));
```
**Flow:** if model has attributes → (posts/pages: load only URL-service-required relations MISSING from the event model; members: force-load three relations) → run the standard admin output serializer with `previous:false` → `current` → if `_changed` non-empty and `_previousAttributes` exist → re-serialize with `previous:true` → pick ONLY changed keys (after rename mapping) → wrap as `{[docName.replace(/s$/,'')]: {current, previous}}`.
**Invariant:** (1) Reloading a relation the event already carries would strip nested roles from the payload — hence "load only missing" via `getRequiredRelations()`; on default routes.yaml it's a no-op. (2) The previous/changed key diff happens in API-SERIALIZED key space, not model key space — the SERIALIZED_KEYS rename map bridges them. (3) Deletion events carry empty current (no attributes), edits carry both.
**Probe:** `grep -cF "getRequiredRelations()" ghost/core/core/server/services/webhooks/serialize.js` → expect `2`; `grep -cF "SERIALIZED_KEYS" ghost/core/core/server/services/webhooks/serialize.js` → expect `2`; `grep -cF "_previousAttributes" ghost/core/core/server/services/webhooks/serialize.js` → expect `1`; direct tests pin behavior incl. tier switch: `grep -cF "it('includes the previous tiers when a member switches between paid tiers'" ghost/core/test/unit/server/services/webhooks/serialize.test.js` → expect `1`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ghost", query: "loadRequiredUrlRelations serialize webhook", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt dual current/previous serialization with missing-relation-only loading and serialized-key rename map. Adapt Bookshelf `load`/`relations` mechanics to host ORM; omit the Ghost URL service.
