<!-- capsule-v2 -->
# Account-limited restriction ledger — how do page-text limit banners become dated ledger rows that gates consult later?

**Source:** growchief AGPL-3.0 `main@abb1e37a`; Codebase Memory `growchief`. **Question:** a social network shows "weekly invitation limit" in page text — how does that transient DOM state become a durable scheduling constraint?

## Banner table → accountLimited poller → restrictions row → throttler gate
**Path/Symbol:** detector `shared/server/bots/providers/linkedin/linkedin.provider.ts:accountLimited` (:137-158) + module `list` table (:27-56); persist `workflow.information.activity.ts:saveRestriction` (:173-187); consult `bots.repository.ts:getStepRestrictions/getActiveRestrictions` (:554-595); consumed by throttle loop (:196-240).
**Signature:** `accountLimited(params): Promise<Omit<Required<ProgressResponse>,'leads'> | false>`; `saveRestriction(botId, methodName, type: RestrictionType)`; RestrictionType = `'weekly'` (progress.response.ts).
**Data Shape:** banner rows `{type:'weekly', char: <page substring>, message: <user-facing text>}`; ledger row `(botId, methodName, until: Date)`.

### Decisive source
```ts
// detection: whole-body text scan against the banner table
const body = await params.page.evaluate(() => document.querySelector('body')?.innerText || '');
const find = list.find((p) => body.indexOf(p.char) > -1);
if (find) return { endWorkflow: false, delay: 0, repeatJob: true,
                   restriction: { type: find.type, message: find.message } };
return false;
```
```ts
// persistence: 'weekly' ⇒ next Monday 00:00 UTC
if (type === 'weekly') {
  const date = dayjs.utc().endOf('week').add(2, 'day').startOf('week').toDate();
  await this._botsService.saveRestriction(botId, methodName, date);
}
```

**Flow:** BotManager's `_findRestrictions` watcher polls `accountLimited` every 5s during any job → non-false result rides back as `restriction` on the ProgressResponse → throttler notifies the org (email+notification under `patched('notifications-01-09-2025')`) and calls `saveRestriction(botId, functionName, restriction.type)` → from then on `getStepRestrictions` gates THAT (bot, action) pair until `until`, feeding the defer-and-swap queue logic. XProvider's twin is honest about not knowing: `await timer(100000); return false`.
**Invariant:** the ledger is keyed by METHOD NAME, so a weekly connection-request limit never blocks messages/likes; `until` is an absolute UTC timestamp computed at save time — no cron needed to lift it; the gate query uses `until: { gt: now }` so expired rows simply stop matching (history preserved for getActiveRestrictions ordering).
**Probe:** no test runner upstream. Deterministic pins: `grep -n 'weekly invitation limit' shared/server/bots/providers/linkedin/linkedin.provider.ts` → :29/:41; dayjs chain :179-184; gate `until: { gt:` bots.repository.ts:559/:583.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "growchief", query: "accountLimited restriction weekly", limit: 10 });
```

## Verdict
Adopt: DOM-sentinel → dated-ledger → dispatch-gate pipeline with per-action granularity and absolute expiry. Adapt banner strings/durations per platform. Omit LinkedIn copy text.
