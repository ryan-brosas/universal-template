<!-- capsule-v2 -->
# cqrs-context-composition — how do I bolt a clean command/query context onto a legacy CRUD source WITHOUT rewriting it, and keep its transaction bound to the host's?

**Source:** lh-basis (Linked Helper extract) **NO LICENSE — learn-only, patterns recorded, zero code copied**; source-read plane `core/local-source/dist/contexts/campaign/**` — the `lh-basis` umbrella graph project indexes only `public-methods`/`models` (BM25 `total: 0` for context symbols is BY CONSTRUCTION), so byte-exact file probes are the anchors. **Question:** how does a production app introduce CQRS handlers over an existing legacy data layer while sharing ONE transaction scope and keeping legacy call sites working?

## Campaign context composition (bind → setup → api facade)
**Path/Symbol:** `contexts/campaign/composition/bindings/index.js:bind` (DI bindings + transaction-provider rebind); `composition/setup/index.js:setup` (handler resolution + `{context, api:{events, commands, queries, legacy}}` facade); `application/inbound/commands/change-hidden-flag/handlers/ChangeHiddenFlagHandler.js`; `application/inbound/queries/assert-collection-not-readonly-handler/handlers/AssertCollectionNotReadonlyHandler.js`.
**Signature:** `bind(container, {dbTransactionProvider}) → (ctx) => container.rebindSync(INFRA_DB_TRANSACTION_PROVIDER).toConstantValue(() => ctx)`; `setup(container, {dbTransactionProvider})` → `{context: {updateDBTransactionProvider}, api: {events: {peopleAction, organizationsAction}, commands: {campaign: {...execute-bound}}, queries: {campaign: {...handle-bound}}, legacy: {guards: {...}}}}`.
**Data Shape:** commands expose `.execute.bind(handler)`; queries expose `.handle.bind(handler)`; guards live under `legacy.guards.<entity>` and map plain args into query objects via `mapAssert*InputToQuery` before calling `.handle`.

### Decisive source
```js
// bind(): the transaction provider starts as a STUB, then rebinds to the real one.
// The returned updater is called by Source AFTER DB init so every handler shares
// the SAME connection/transaction scope as legacy writes.
container.bind(INFRA_DB_TRANSACTION_PROVIDER).toConstantValue(opts.dbTransactionProvider);
/* …bindAction/bindCampaign/… per-entity module bindings… */
return ctx => container.rebindSync(INFRA_DB_TRANSACTION_PROVIDER)
                       .toConstantValue(() => ctx);
// ChangeHiddenFlagHandler.execute — guard → mutate aggregate → versioned append → save → publish
const campaign = await this.campaignRepo.getOneById(liAccountId, campaignId);
if (!campaign) throw new CampaignNotFoundError(liAccountId, campaignId);
const expectedVersion = campaign.getVersion();
campaign.changeHiddenFlag(flagValue);
const events = campaign.pullPendingEvents();
if (events.length !== 0) {
  await this.eventRepo.append(campaignId, events, expectedVersion);   // optimistic concurrency
  await this.campaignRepo.save(campaign);
  await this.eventBus.publish(events);
}
// AssertCollectionNotReadonlyHandler.handle — a GUARD IS A QUERY HANDLER
const access = (await this.campaignLegacyAccessRepo.findCampaignAccessesByCollectionId(input))
  .find(a => a.isReadonly);
if (access) throw new CampaignReadonlyError(access.liAccountId, access.campaignId);
```

**Flow:** bootstrapper calls `setup(container, {dbTransactionProvider})` once per context → `bind` registers infrastructure + per-entity handler modules → setup resolves ~30 token-keyed handlers from the container and returns the facade → legacy `Source` finishes DB init and invokes `context.updateDBTransactionProvider(ctx)` swapping the stub for the live provider → legacy sources now call `api.legacy.guards.campaign.assertVisible(...)` (mapper→query→handler) while new code uses `api.commands`/`api.queries`; domain events flow out through `api.events.*Action.publish*` mappers onto per-aggregate event buses.
**Invariant:** write handlers follow ONE ordering — visibility/write-allowed guard FIRST, then optimistic-version event append, then repo save, then bus publish (a handler that throws publishes nothing); read/guard handlers NEVER mutate and express denial as typed domain errors (`CampaignReadonlyError`, not booleans); the DI token for the transaction provider is REBOUND, never duplicated, so exactly one connection scope serves both planes; the facade is the ONLY sanctioned entry — handlers are never resolved ad hoc at call sites.
**Probe:** no public tests (proprietary dist extract) — coverage caveat recorded. Byte-exact probes anchored at `lh-basis/core/local-source/dist`: `grep -c 'rebindSync' contexts/campaign/composition/bindings/index.js` ⇒ 1; `grep -c 'toConstantValue(n.dbTransactionProvider)' contexts/campaign/composition/bindings/index.js` ⇒ 1; `ls contexts/campaign/composition/bindings/*.js | wc -l` ⇒ 9 binding modules; `grep -c 'pullPendingEvents' …/change-hidden-flag/handlers/ChangeHiddenFlagHandler.js` ⇒ 1; `grep -c 'CampaignReadonlyError' …/assert-collection-not-readonly-handler/handlers/AssertCollectionNotReadonlyHandler.js` ⇒ 1; `grep -o 'assertVisible' contexts/campaign/composition/setup/index.js | wc -l` ⇒ 6 (campaign/action/actionResult guard families; file is minified single-line, `grep -c` would yield 1); `grep -c 'legacy' contexts/campaign/composition/setup/index.js` ⇒ 1.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "lh-basis", query: "setupContexts campaign", limit: 4 });
// resolves public-methods models/campaigns guards (isICampaign…) — the CONSUMER side;
// context-internal classes are NOT indexed (umbrella root excludes core/local-source) — expected.
```

## Verdict
Adopt the composition shape: token-keyed DI modules per entity, a `{commands, queries, events, legacy-guards}` facade as single entry, transaction-provider rebinding as the seam that gives new handlers the host's transaction, and guards-as-query-handlers with typed denial errors. Adapt naming/mapping to your framework. Omit the inversify specifics if you use another DI container. **No-license repo: patterns only, zero code copied.** This closes the standing pass-22/23 conditional "lh-basis contexts/campaign CQRS read-model plane IF that porting question fires."
