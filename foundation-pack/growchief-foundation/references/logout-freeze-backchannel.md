<!-- capsule-v2 -->
# Logout freeze back-channel — when a browser job discovers the account logged out mid-run, how does the whole account fleet freeze WITHOUT dropping queued work?

**Source:** growchief AGPL-3.0 `main@abb1e37a`; Codebase Memory `growchief`. **Question:** session death is detected deep inside one browser job — what tells every other queued job to stand down, and what un-freezes them?

## Bidirectional boolean signal; DB column is durable truth, signal is instant push
**Path/Symbol:** producers `shared/server/bots/bot.manager.ts` (pre-race lead race :548-556; post-race branch :748-757) → `shared/server/database/bots/bots.service.ts:loggedOut` (:214-251, false) and `:saveStorageAndActions` (:281-304, true); consumer `apps/orchestrator/src/workflows/workflow.throttle.ts` (handler :137-139; DB re-sync :242; gate :259).
**Signature:** `loggedOut(bot: string): Promise<boolean>`; `saveStorageAndActions(..., loggedIn: boolean, ...)` fans out iff `functionName === 'login' && loggedIn && saveBot.id`; boolean-payload signal.
**Data Shape:** `Bot.logged` DB column = durable flag (written transactionally at login, bots.repository.ts:443-508); throttler-local `logged`/`active` booleans = volatile mirrors.

### Decisive source
```ts
// consumer side
setHandler(botLoggedSignal, async (w) => { logged = w; });   // :137-139
logged = botModel?.logged || false;                          // :242 re-sync EACH iteration
await condition(() => active && logged);                     // :259 deadline-less gate

// producer side
await handle.signal('botLoggedSignal', false);               // :230 logout fan-out
await handle.signal('botLoggedSignal', true);                // :295 login fan-out
```

**Flow:** EITHER logout watcher resolves ('logout' from the pre-race lead-resolution race :548-556 or the main heptathlon race :748-757) → `loggedOut()` lists every RUNNING throttler of that bot and fans `false`, plus an urgent user notification → dispatch gate freezes the queue; successful LOGIN saves storageState first, then fans `true`; meanwhile every loop iteration re-reads the DB row, so the mirror self-heals even if a signal was lost.
**Invariant:** FREEZE-NOT-DROP — queued Work stays intact (queries report false while frozen; nothing is spliced), the gate has NO deadline (unlike the bounded restriction-wait condition), so a forgotten re-login parks the account forever BY DESIGN; the detecting job returns `{ delay: 0, endWorkflow: false, repeatJob: true }` WITHOUT saving storageState (retry later, maybe after human re-login).
**Probe:** no upstream tests exist. Deterministic pins (executed): `grep -n "setHandler(botLoggedSignal\|logged = botModel?.logged\|condition(() => active && logged)" apps/orchestrator/src/workflows/workflow.throttle.ts` → :137/:242/:259; `grep -n "handle.signal('botLoggedSignal'" shared/server/database/bots/bots.service.ts` → :230/:295; `grep -n "=== 'logout'" shared/server/bots/bot.manager.ts` → :548/:749.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "growchief", query: "botLoggedSignal loggedOut", limit: 6 });
```

## Verdict
Adopt: bidirectional freeze flag fanned instantly to all per-account loops, backed by a durable DB flag re-synced each iteration; pair with a deadline-less gate only when freezing (not cancelling) is the intent. Adapt signal naming/notification plumbing. Omit the hardcoded notification URL (postiz.com). Caveat: complements storage-state-session-persistence (WHEN state is saved) and browser-run-race-heptathlon (detection); this capsule owns the fleet-wide freeze contract.
