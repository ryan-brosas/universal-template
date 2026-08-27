<!-- capsule-v2 -->
# Cross-plane status projection — how does an admin UI get ONE honest bot status when truth lives in database rows, restriction ledgers, workflow handles, and live queue state?

**Source:** growchief AGPL-3.0 `main@abb1e37a`; Codebase Memory `growchief`. **Question:** four stores each hold part of "what is this bot doing right now" — what is the merge order and the degradation ladder?

## DB facts first, workflow facts best-effort, tenant check silent, live query last
**Path/Symbol:** `shared/server/database/bots/bots.service.ts:BotsService.getBotStatus` (:425-510).
**Signature:** `async getBotStatus(organizationId: string, botId: string): Promise<any>`.
**Data Shape:** composite `{ found, workingHours: { isWithinHours, timeUntilWorkingHours: Date|null }, restrictions, stepId?, workflowId?, when?, stepDetails? }`; `workingHours` parses stored JSON else falls back to hardcoded `[[540,1020],[540,1020],[540,1020],[540,1020],[540,960],[],[]]` (minutes-of-day windows Mon–Fri + Sat half-day, Sunday off).

### Decisive source
```ts
const bot = await this._botsRepository.getBotById(botId, organizationId);
if (!bot) return { found: false, error: 'Bot not found' };
const workingHours = JSON.parse(bot.workingHours || DEFAULT_HOURS_JSON);
const activeRestrictions = await this._botsRepository.getActiveRestrictions(botId);
const handle = await this._temporal.getClient()
  .getWorkflowHandle('user-throttler-' + botId);        // DERIVED id, never stored
const workflow = await awaitedTryCatch(() => handle.describe());
if (!workflow) return { found: false, workingHours: {...}, restrictions };  // degrade, keep DB truth
if (workflow?.typedSearchAttributes?.get(orgId) !== organizationId)
  return { found: false };                              // silent cross-tenant denial
const query = await handle.query(botJobsQueries);       // live head-job probe
return { ...query, workingHours: {...}, restrictions, stepDetails, found: true };
```

**Flow:** bot-row ownership check (scoped by org) → derive working-hours facts from DB JSON + timezone → load dated restriction rows → `describe()` the DERIVED singleton id inside awaitedTryCatch → absent workflow ⇒ honest degraded answer still carrying hours + restrictions → tenant attribute mismatch ⇒ bare `{found:false}` → live `botJobsQueries` query returns current head job {stepId, workflowId, when} → join DB step display details → final composite.
**Invariant:** planes degrade INDEPENDENTLY — a dead/absent workflow never erases DB-derived facts, and cross-tenant access is indistinguishable from absence (no existence leak via shape or timing); relative ms-until-open converts to an absolute `Date` at the projection edge so clients never redo clock math.
**Probe:** no upstream tests exist. Deterministic pins (executed): `grep -n '540,1020\|getActiveRestrictions\|botJobsQueries' shared/server/database/bots/bots.service.ts` → :435/:444/:471; tenant-check line read directly at :467-469.
**Why a porter gets it wrong:** merging live-first makes a scheduler outage look like "bot idle"; merging the tenant-check last leaks workflow existence across orgs.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "growchief", query: "getBotStatus botJobsQueries", limit: 5 });
```

## Verdict
Adopt: DB-first composition with per-plane degradation and silent tenant denial; derived-handle describe with swallowed failure. Adapt plane set to your stores. Omit the hardcoded default-hours constant (product policy). Caveat: the tenant-check FRAGMENT also appears in temporal-multitenant-control-plane as fan-out evidence — this capsule claims the full projection ladder, not the fragment.
