<!-- capsule-v2 -->
# Working-hours interval algebra — how do I compute "is now inside this account's schedule" and the next allowed send time when schedules nest (global + per-action) and can be randomized daily?

**Source:** lh-basis (Linked Helper extract) NO LICENSE — learn-only, patterns recorded, zero code copied `extract mtime 2026-08-15`; Codebase Memory projects `lh-basis-source` (+`lh-basis-migrations`). **Question:** given per-account weekly working intervals that can be overridden per campaign action and shifted by a random daily offset, what is the correct algorithm to test "can I act right now" and derive the closest future working date — including the day+night wraparound trap?

## Scope-filtered interval search → adjustments merge → invert/intersect ladder

**Path/Symbol:** `Source/Source.WorkingHours.js:_isCurrentDateInWorkingInterval`, `_getCalculatedIntervals`, `_alignWeekIntervalsWithGlobalWeekIntervals`, `_getRandomWorkingHoursTimeshift`; `helpers/adjustments.js:calculateRandomAdjustmentForWorkingInterval`; schema twins `WorkIntervals/WeekWorkingIntervalRepo.js:weekWorkingIntervalRepo` (`dayAndNight` derived column) and `migrations/169.js` (`working_intervals_adjustments` UNIQUE(li_account_id, campaign_id, action_id, working_week_day), timeshift DEFAULT 15).
**Signature:** `_isCurrentDateInWorkingInterval(db, liAccount, scope) -> bool`; `_getCalculatedIntervals(db, liAccount, scope, includeGlobal=false, invertGlobal=true)`; `_getRandomWorkingHoursTimeshift(liAccountId, interval, adjustmentRow) -> int minutes`.
**Data Shape:** interval row = `{liAccountId, campaignId|null, actionId|null, dayOfWeek, start, end, dayAndNight}` where `start/end` are MINUTES from midnight (null = not set); adjustment row = `{workingWeekDay, isEnabled, timeshift}` keyed `(liAccount, campaign?, action?, weekday)`; scope = `{type:'global'} | {type:'action', campaignId, actionId}`.

### Decisive source
```js
// 1) CURRENT-TIME TEST: all-day/night intervals short-circuit TRUE before any
//    adjustment math; otherwise an enabled adjustment shifts start forward:
const intervals = repo.search(db, { filters: { liAccountId: In([id]),
    dayOfWeek: In([dow]), start: LessOrEqualThan(dayDistance),
    end: GreatOrEqualThan(dayDistance) }, scopes: [scope] });
if (intervals.length > 0 && intervals.every(i => i.dayAndNight)) return true;
const adj = adjustmentsFor(scope)[dow];
if (!adj?.isEnabled) return intervals.length > 0;
return intervals.some(i => { const t = randTimeshift(id, i, adj);
                             return i.start + t <= dayDistance; });

// 2) SCHEDULE COMPOSITION for "next date": merge action intervals; when the
//    GLOBAL scope joins, global is INVERTED into blocked time unless asked:
function alignWithGlobal(actionIvs, globalIvs, useGlobalDirectly) {
  return useGlobalDirectly
    ? WeekWorkingInterval.intersect(globalIvs, actionIvs)
    : WeekWorkingInterval.merge(WeekWorkingInterval.invert(globalIvs), actionIvs); }

// 3) DETERMINISTIC DAILY RANDOMNESS: seeded by (UTC midnight, account, dow,
//    ids) so every worker recomputes the SAME shift for the same day:
function getDailyRandomPercentage(...key) {
  const now = new Date();
  return calculatePercentageAdjustment(
    new Date(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate()).getTime(), ...key); }
// shift = round(timeshift * (1 - pct/100)); ZERO if interval too short to shift
```

**Flow:** read intervals filtered by account+weekday+minute-window under the scope's pre-grouped filter set → if every hit is a `dayAndNight` interval, answer TRUE immediately → load that weekday's adjustment (global or campaign-action level) → disabled adjustment ⇒ plain membership; enabled ⇒ re-test with each interval's start shifted by the deterministic daily random amount → for closest-date queries, merge the action's merged intervals with the global schedule via intersect-or-invert-merge depending on whether global should constrain or complement.
**Invariant:** the UTC-midnight seed makes the random shift STABLE within one day across processes but DIFFERENT across days — never replace it with unseeded randomness (breaks reproducibility) or a fixed offset (defeats detection avoidance). The all-day-and-night short-circuit must run BEFORE adjustment logic because a shifted start on a 24h interval would wrongly exclude the tail hours. Global-vs-action composition has two legal directions only: intersect (global constrains) or inverted-merge (global blocks); merging both positively double-counts overlap. `start/end` null means "not configured" and such rows pass through untouched. Storage keeps `day_and_night` as a DERIVED column (`toColumn`/`fromRow` recompute it from start/end via `WeekWorkingSchedule.isDayAndNight`) so the wraparound flag can never disagree with the bounds it was derived from.
**Probe:** no public tests (proprietary extract) — coverage caveat recorded. Deterministic probes (all verified at extract; lh-basis dist files are MINIFIED single-line — use `grep -cF` fixed-string counts, never `wc -l` line-counts): migration 169 creates `working_intervals_adjustments` with `UNIQUE (li_account_id, campaign_id, action_id, working_week_day)` and backfills `timeshift INTEGER NOT NULL DEFAULT 15` (`grep -cF` ⇒ 1) only from NON-dayAndNight bounded rows — the WHERE is multi-line SQL with embedded-`\n` literals in the minified file: `grep -oF 'working_intervals.started_at IS NOT NULL' 169.js | wc -l` ⇒ 1 and same for `working_intervals.ended_at IS NOT NULL` ⇒ 1, `day_and_night = 0` ⇒ 1 (a bare `grep -c "day_and_night = 0 AND started_at…"` string NEVER matches); migration 34 adds `day_and_night INTEGER NOT NULL DEFAULT 0` rebuilding `new_working_intervals` (⇒3 occurrences incl. rename pairs); graph anchor `lh-basis-source.Source.WorkingHours._getRandomWorkingHoursTimeshift` resolves (Function, Source.WorkingHours.js).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "lh-basis-source", query: "adjustments timeshift", limit: 10 });
await mcp.codebase_memory.search_graph({ project: "lh-basis-migrations", semanticQuery: ["create working_intervals table day_and_night column"], limit: 10 });
```

## Verdict
Adopt the three contracts: minute-of-day window test over scope-nested weekly intervals, deterministic-seeded daily jitter bounded by a configurable timeshift, and the intersect-vs-inverted-merge rule for composing a personal schedule with a base schedule. Adapt interval storage to your DB (the derived dayAndNight column pattern ports cleanly wherever wraparound spans exist); omit vendor plumbing. Contrast growchief's working-hours-signal-invalidation (same problem space, Monday-first `[startMin,endMin]` arrays): lh-basis adds per-action overrides + randomized shifts — adopt the simpler arrays for single-schedule bots, the nesting+jitter contracts when multiple campaigns share one account. Patterns only — no-license source.
