<!-- capsule-v2 -->
# webhook condition evaluator — how does an in-process filter engine mirror SQL filter semantics (dates, users, blanks, groups) without touching the database?

**Source:** NocoDB Sustainable Use License `develop@640fe3b06fb26c9d000e2258477001c0d5e62c73`; Codebase Memory project `mnt-hdd-utopia-inspo-platforms-nocodb`. **Question:** Hook triggers decide in Node from the raw row payload — what is the complete operator surface, and where does it deliberately DIVERGE from the SQL filter compiler?

## Recursive JS-side Filter walk with dayjs date algebra + user-field set logic

**Path/Symbol:** `packages/nocodb/src/helpers/webhookHelpers.ts:validateCondition` (:66–396), `parseBody` (:45–64), `sanitizeUserForHook` (:401–414), `handleHttpWebHook` (:440–451), `invokeWebhook` (:453–472 — thin back-compat delegate to `new WebhookInvoker().invoke`), `_transformSubmittedFormDataForEmail` (:474–501).
**Signature:** `validateCondition(context, filters: Filter[], data: any = {}, {client, skipFetchingChildren?}: {client: string; skipFetchingChildren?: boolean}): Promise<boolean | null | undefined>`; `parseBody(template, data, vars?)` compiles Handlebars with `{noEscape: true}` and context `{data, event: data, vars}`.
**Data Shape:** `data` keys are column TITLES; user fields carry `{id}` objects or id arrays; date columns compare at DAYJS 'day' granularity with client-dependent formats (`mysql2` → `'YYYY-MM-DD HH:mm:ss'`, else `'YYYY-MM-DD HH:mm:ssZ'`).

### Decisive source
```ts
// :82-95 — three-valued fold over the group
let isValid = null;
for (const _filter of filters) {
  ...
  if (filter.is_group) {
    filter.children = skipFetchingChildren ? filter.children || [] : filter.children || (await filter.getChildren(context));
    res = await validateCondition(context, filter.children, data, {client, skipFetchingChildren});
```

**Flow:** empty filters ⇒ true → per leaf: date/datetime/created/modified columns take a dedicated branch — month-format meta resets BOTH sides to the 1st (`isDateMonthFormat`), sub-ops rewrite filterVal relative to `now` (today/tomorrow/yesterday/oneWeekAgo/oneWeekFromNow/oneMonthAgo/oneMonthFromNow/daysAgo/daysFromNow/exactDate/pastWeek/pastMonth/pastYear/nextWeek/nextMonth/nextYear/pastNumberOfDays/nextNumberOfDays), ops map to dayjs isSame/isAfter/isBefore/isSameOrBefore/isSameOrAfter/'day', `isWithin` uses isBetween(filterVal, now) for past-* and isBetween(now, filterVal) for next-*; missing filterVal on parameterized sub-ops returns UNDEFINED (fails the hook silently). User/CreatedBy/LastModifiedBy columns extract ids then apply anyof/nanyof/allof/nallof/empty/notempty with DEFAULT→false for unsupported ops. Generic leaves do loose eq (`==`), like/nlike via case-insensitive indexOf, recursive-array blank detection, checked/null ops, comma-split allof/anyof. Fold: logical_op or → `isValid = isValid || !!res`; not → `isValid = isValid && !res`; and/default → `(isValid ?? true) && res`.
**Invariant:** (1) Three-valued accumulator: null start means an OR group of all-undefined stays null-ish rather than true; porters who seed with false flip OR semantics. (2) This is a SECOND implementation of filter semantics (JS-side) parallel to conditionV2 (SQL-side) — they must be changed in tandem when adding operators; divergence here is invisible to tests that only cover one side. (3) `skipFetchingChildren` exists for JSON-stored filters ("like workflow configs") that aren't in the database (:87–89 comment).

### Porting traps (each verified against source)
- parseBody swallows compile errors and returns the ORIGINAL template (:60–63) — template bugs degrade to literal-text payloads instead of failing hooks.
- sanitizeUserForHook whitelists exactly {id, email, display_name} and requires both id AND email else returns null (:401–414).
- In-file anchors: `grep -c "noEscape: true" src/helpers/webhookHelpers.ts` → 1; `grep -c 'isBetween' …` → 4; `grep -c 'sanitizeUserForHook' …` → 1; `grep -n "case 'not':" …` → :386.

**Probe:** Deterministic probe from repo root:
`cd packages/nocodb && grep -n 'isValid = isValid || !!res' src/helpers/webhookHelpers.ts | cut -d: -f1` → `384` and `grep -o 'YYYY-MM-DD HH:mm:ss' src/helpers/webhookHelpers.ts | wc -l` → `2` (BOTH format strings share one line — count occurrences, not lines).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-nocodb", query: "validateCondition webhookHelpers invokeWebhook handlebars", limit: 10 });
```
Resolves `invokeWebhook` :453-472 rank-1, `validateCondition` :66-396 rank-2 (note the nc-gui `FormFilters.validateCondition` twin at rank-3 is FRONTEND — wrong plane for this capsule).

## Verdict
Adopt the operator table + three-valued fold + day-granularity date algebra as the JS-side twin of your SQL filter grammar; adapt dayjs to host date lib; omit axios/Handlebars specifics. Coverage caveat: no direct tests at pin; probes are source-greps.
