<!-- capsule-v2 -->
# Week working schedule — How is a weekly working calendar encoded so day keys, defaults, and bounds cannot drift?

**Source:** Linked Helper v2.130.5 ingest (proprietary — citations-only), pin `?@?`; Codebase Memory `lh-basis` @ gen 2026-08-23T00:11:49Z. **Question:** how does the kernel represent "which days of the week are working days" plus the minute arithmetic that bounds scheduling windows — without a date library?

## A getDay()-compatible day enum plus derived constants and two canonical grids
**Path/Symbol:** `core/public-methods/models/workingHours/enums.js` — `DayOfWeek` (6–15); `core/public-methods/models/workingHours/intervals/WeekWorkingSchedule.js` — `IWeekWorkingSchedule` namespace as constants module (7–30).
**Signature:** `DayOfWeek`: reverse-keyed TS enum, `sunday=0 … saturday=6`. `IWeekWorkingSchedule.MinInHours/MinInDay/MinInWeek: number`; `.EMPTY_WORKING_SCHEDULE / .DEFAULT_WORKING_SCHEDULE: {[day:number]: boolean}`.
**Data Shape:** schedule maps carry exactly seven NUMERIC keys computed from enum members; bounds are DERIVED (`MinInDay = 24*MinInHours`, `MinInWeek = 7*MinInDay`) rather than written as literals.

### Decisive source
```js
// enums.js
DayOfWeek[DayOfWeek["sunday"] = 0] = "sunday";
// ... monday=1 ... saturday=6
// intervals/WeekWorkingSchedule.js
IWeekWorkingSchedule.MinInHours = 60;
IWeekWorkingSchedule.MinInDay = 24 * IWeekWorkingSchedule.MinInHours;
IWeekWorkingSchedule.MinInWeek = 7 * IWeekWorkingSchedule.MinInDay;
IWeekWorkingSchedule.EMPTY_WORKING_SCHEDULE = {
    [enums_1.DayOfWeek.monday]: false,
    /* ...tuesday..sunday all false... */
};
IWeekWorkingSchedule.DEFAULT_WORKING_SCHEDULE = {
    [enums_1.DayOfWeek.monday]: true,
    /* ...tuesday..sunday all true... */
};
```

**Flow:** `TInterval` ordered minute pairs `[start,end]` (see interval-and-limit-guards) ride inside these per-day enablement grids; the minute ladder bounds every window so no magic number can drift from the definition.
**Invariant:**
1. **`DayOfWeek` numbering equals JavaScript's `Date#getDay()`** (sunday=0..saturday=6) — runtime boundaries convert with zero glue code, and the schedule maps key directly on enum members, so a day value from a Date can index the map unchanged.
2. **Numeric keys enumerate in ORDINAL order, not insertion order.** The source inserts monday→sunday, but JS orders integer-like keys ascending numerically — iteration is sunday-first. Probe-verified below: `Object.keys(EMPTY_WORKING_SCHEDULE)` → `0,1,2,3,4,5,6`. After a JSON round-trip the keys become strings; consumers must re-number before indexing.
3. **Default posture is ALWAYS-WORKING.** `DEFAULT_WORKING_SCHEDULE` is all-true: an absent/unconfigured calendar does not mean closed. `EMPTY_WORKING_SCHEDULE` (all-false) is the explicit closed calendar — two distinct canonical states.

**Probe (executed pass 14, deterministic node-require against shipped dist modules):**
```bash
node -e "const d=require('/mnt/hdd/utopia/inspo/lh-basis/core/public-methods/models/workingHours/enums.js').DayOfWeek;const s=require('/mnt/hdd/utopia/inspo/lh-basis/core/public-methods/models/workingHours/intervals/WeekWorkingSchedule.js').IWeekWorkingSchedule;console.log(d.sunday,d.saturday,s.MinInDay,s.MinInWeek,Object.keys(s.DEFAULT_WORKING_SCHEDULE).length,Object.keys(s.EMPTY_WORKING_SCHEDULE)[0]==='1',s.EMPTY_WORKING_SCHEDULE[d.sunday])"
```
→ observed `0 6 1440 10080 7 false false` — the `[0]==='1'` check is FALSE because enumeration is ordinal-first (`0` = sunday first); follow-up probe printed `Object.keys(EMPTY).join(',')` → `0,1,2,3,4,5,6`, confirming invariant 2 live.

## Get live surrounding code
**Retrieve (executed pass 14):**
```ts
await mcp.codebase_memory.search_graph({ project: "lh-basis", name_pattern: "^(InterestTypes|RecommendationTypes|DayOfWeek|IWeekWorkingSchedule)$" });
```
→ observed exactly 4 rows: `IPersonInterest.InterestTypes 6-6`, `IPersonRecommendation.RecommendationTypes 6-6`, `workingHours.enums.DayOfWeek 6-6`, `intervals.WeekWorkingSchedule.IWeekWorkingSchedule 7-7`.

## Verdict
Adopt: getDay()-aligned day ordinals, arithmetically-derived minute bounds, and explicit always-on vs closed canonical grids. Adapt: prefer string day keys or an array-of-7 in hosts where JSON consumers outnumber JS ones (removes the re-numbering hazard). Omit: the engine's scheduler semantics that consume these grids (excluded dist plane). Coverage: both cited files fully indexed (`no_recorded_issue` @ gen 2026-08-23T00:11:49Z); no test runner in ingest — deterministic probes above are the executable evidence.

Cross-references: interval-and-limit-guards (the TInterval windows this grid enables per day); scalar-taxonomy-guards (unguarded-ordinal-enum style — DayOfWeek ships without a membership guard too).
