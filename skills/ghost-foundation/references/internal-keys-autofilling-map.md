<!-- capsule-v2 -->
# Internal key AutoFillingMap — how do in-process integrations get their API keys without per-request lookups?

**Source:** Ghost MIT `main@81292b004cf59591f03d7dbe01f28f31c09ee813`; Codebase Memory `ext-ghost`. **Question:** How is the scheduler's own admin key cached, and how does rotation invalidate it?

## internal-keys singleton
**Path/Symbol:** `ghost/core/core/server/services/internal-keys/index.ts:internalKeys` (:1–46).
**Signature:** `AutoFillingMap<InternalIntegrationSlug, Promise<InternalApiKey>>` with factory `(slug) => models.Integration.getApiKeyBySlug(slug, SLUG_KEY_TYPE[slug])`.
**Data Shape:** slugs `'ghost-scheduler' | 'ghost-internal-frontend'`; seeded types pinned `{ghost-scheduler: 'admin', ghost-internal-frontend: 'content'}`; values are PROMISES (single-flight dedupe of concurrent gets).
### Decisive source
```ts
const internalKeys = new AutoFillingMap<InternalIntegrationSlug, Promise<InternalApiKey>>((slug) =>
  models.Integration.getApiKeyBySlug(slug, SLUG_KEY_TYPE[slug]),
);
// Rotation orchestration calls `.clear()` to invalidate after rotating the
// underlying api_keys row.
```
**Flow:** consumer (`post-scheduling` constructor events, `rescheduleAll`) awaits `internalKeys.get('ghost-scheduler')` → first call hits DB via the seed-fixture-backed integration → promise cached process-lifetime → rotation flow rotates the api_keys row, calls `.clear()`, and PostScheduling.rescheduleAll({previousKey}) re-signs queued jobs under the new secret.
**Invariant:** Values are PROMISES not keys — concurrent first getters share one DB query and one resolved value (no torn cache). The slug→type mapping is encoded here so callers can't request an admin key for a content-keyed integration. Rotation correctness depends on the rescheduleAll previousKey contract (see scheduler-event-ladder capsule): unschedule URLs must be signed with the OLD secret to match what the adapter holds.
**Probe:** `grep -cF "'ghost-scheduler': 'admin'" ghost/core/core/server/services/internal-keys/index.ts` → expect `1`; `grep -cF "AutoFillingMap<InternalIntegrationSlug, Promise<InternalApiKey>>" ghost/core/core/server/services/internal-keys/index.ts` → expect `2` (type alias + constructor); graph anchor: `search_graph "internalKeys singleton api key cache slug"` resolves `models/integration.js:getApiKeyBySlug` (:129–143).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ghost", query: "getApiKeyBySlug integration", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt promise-valued autofill cache + explicit clear-on-rotate. Adapt slug vocabulary; keep single-flight semantics or boot storms will multi-query the key table.
