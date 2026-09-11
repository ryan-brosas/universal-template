<!-- capsule-v2 -->
# Working-hours intervals & limit types — How are scheduling windows and metered action budgets validated?

**Source:** Linked Helper v2.130.5 ingest (proprietary — citations-only), pin `?@?`; Codebase Memory `lh-basis` @ 2026-08-23T00:11:49Z. **Question:** what exact shapes do the scheduler's time windows and the credits ledger's capability rows take?

## Ordered pair intervals + capability-object limits
**Path/Symbol:** `core/public-methods/models/workingHours/intervals/guards.js:isTInterval` (7–9); `core/public-methods/models/limits/LimitType/guards.js` — `isTDefaultLimitType` (10–12), `isILimitType` (13–19); `constants.js:ALL_DEFAULT_LIMIT_TYPES` (34 action kinds).
**Signature:** `isTInterval(data): boolean`; `isILimitType(value): boolean`; `isTDefaultLimitType(value): boolean`.
**Data Shape:** interval = `[start:number, end:number]` ordered pair, `start <= end` (equality legal — a zero-length window). LimitType row = dbItem + `type:string ∈ ALL_DEFAULT_LIMIT_TYPES` + `limits` property + credit-method surface `{getCreditsUsed, getCreditsWillBeAvailableDate, useCredits}`.

### Decisive source
```js
function isTInterval(data) {
    return Array.isArray(data) && data.length === 2 &&
        isNumber(data[0]) && isNumber(data[1]) && data[0] <= data[1];   // ORDERED pair, <= allows point windows
}
function isILimitType(value) {
    return (isIDBItem(value) &&
        objectHasStringProperties(value, ['type']) &&
        isTDefaultLimitType(value.type) &&          // membership in the 34-kind closed list
        objectHasProperties(value, ['limits']) &&
        objectHasMethods(value, ['getCreditsUsed', 'getCreditsWillBeAvailableDate', 'useCredits']));
}
// constants.js (excerpt of ALL_DEFAULT_LIMIT_TYPES):
// 'ProfileLoadViaURL', 'Invite', 'Message', 'InMail', 'Endorse', 'Follow',
// 'InviteOverWeeklyLimit', 'GetEmailFromPAS', 'SendPersonToWebhook', ... (34 total)
```

**Flow:** interval guard rejects wrong arity, non-numbers, and inverted ranges at the boundary so downstream scheduling arithmetic can assume `start <= end`. LimitType validation composes the standard recipe (dbItem ∧ typed ∧ shape) but adds a METHOD surface: a limit row must expose its credit-ledger API, because consumers call `useCredits` directly.
**Invariant:** time windows are canonicalized at validation (never normalized later); capability limits are objects WITH behavior — a plain `{type:'Invite'}` literal is NOT a usable limit even though its type string is legal.
**Probe:** `node -e` against dist guards: `isTInterval([9,17])` true; `[17,9]` false; `[9,9]` true; `[9]` false; `isILimitType({id:1,type:'Invite',limits:{},getCreditsUsed(){},getCreditsWillBeAvailableDate(){},useCredits(){}})` true; type:'Nope' false; valid type but missing `useCredits` method false.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "lh-basis", query: "working hours daily limits guards interval", limit: 10 });
```

## Verdict
Adopt validated-at-boundary ordered pairs for any window arithmetic and capability-object guards (data + method surface) for metered resources. Adapt the limit-type list to your product's action taxonomy. Omit the specific LinkedIn action names. Coverage: no_recorded_issue on cited files; probes executed against shipped dist modules (no test runner in ingest).
