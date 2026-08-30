<!-- capsule-v2 -->
# storageState session persistence — when is login state saved, and which outcomes must NOT save it?

**Source:** growchief AGPL-3.0 `main@abb1e37a`; Codebase Memory `growchief`. **Question:** a bot reuses a logged-in browser profile across runs; what is the exact save/skip policy around `browser.storageState()`?

## Load unless login; save on every non-poisoned outcome
**Path/Symbol:** `shared/server/bots/bot.manager.ts` (load :82-107 + :92-96; save :692-699; post-race branch :709-756) + `shared/server/database/bots/bots.repository.ts:saveStorageAndActions` (:429-509).
**Signature:** `getContext(launch, functionName, botInformation, proxy)` → `launch.newContext({ viewport, userAgent, ...(storage && functionName !== 'login' ? { storageState: JSON.parse(storage) } : {}), ...proxy })`; save side `browser.storageState()` → `saveStorageAndActions(functionName, orgId, platform, name, picture, id, groupId, bot, state, race !== 'logout' && race !== false, timezone, proxyId)`.
**Data Shape:** storage = Playwright storageState JSON stringified in the `bot.storage` column; identity upsert keyed by unique `(organizationId, platform, internalId)`.

### Decisive source
```ts
// proxy failure ⇒ retry later WITHOUT saving the (possibly broken) new state:
if (race === 'proxy') return { delay: 1_800_000, endWorkflow: false, repeatJob: true };
// ui-error object ⇒ repeat, also skipping saveStorageAndActions:
if (typeof race === 'object' && !Array.isArray(race) && 'type' in race)
  return { delay: 0, endWorkflow: false, repeatJob: true };
await this._botService.saveStorageAndActions(..., state,
  race !== 'logout' && race !== false, timezone, proxyId);
if (race === 'logout') { await this._botService.loggedOut(bot);
  return { delay: 0, endWorkflow: false, repeatJob: true }; }
```
```ts
// repository — concurrent-bot-safe upsert inside ONE transaction:
const { logged, id } = await this._prisma.$transaction(async (prism) => {
  if (!bot && name && platform && internalId && orgId) {
    const { id } = await prism.bot.upsert({
      where: { organizationId_platform_internalId: { organizationId: orgId, platform, internalId } },
      create: {...}, update: { ..., deletedAt: null } });   // resurrect soft-deleted
    ...
```

**Flow:** context created fresh per job (never reuse contexts across bots); after the run, tracing stops, screenshots stop, page closes, THEN state is captured and persisted; `logged` boolean derives from the outcome sentinel (`logout`/`false` ⇒ logged-out), and a successful LOGIN flips the throttler's gate via signal fan-out (`botLoggedSignal(true)` to every running throttler for that bot).
**Invariant:** `'proxy'` and ui-error paths return BEFORE `saveStorageAndActions` — a poisoned session (bad network / crashed automation) must never overwrite the last known-good storageState; the upsert transaction comment names the hazard it solves ("two bots trying to update the context at the same time").
**Probe:** no test runner upstream. Deterministic pins: `grep -n "race === 'proxy'" shared/server/bots/bot.manager.ts` → :710; `grep -n '\$transaction' shared/server/database/bots/bots.repository.ts` → :441; unique-key upsert :447-450.
**Coverage caveat:** behavior inferred from code order — no test asserts the skip-save ordering.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "growchief", query: "saveStorageAndActions storageState getContext", limit: 10 });
```

## Verdict
Adopt: per-job fresh context + load-unless-login + save-only-on-clean-outcome + single-transaction identity upsert. Adapt storage location (DB column here). Omit the specific sentinel set if your outcomes differ.
