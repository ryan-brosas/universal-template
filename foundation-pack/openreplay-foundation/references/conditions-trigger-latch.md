<!-- capsule-v2 -->
# ConditionsManager trigger-once — how does "start recording when X happens" evaluate without double starts?

**Source:** openreplay AGPL-3.0 (tracker MIT) `main@99eb600`; Codebase Memory `openreplay`. **Question:** What message-driven rule engine shape lets a porter implement conditional session capture safely?

## Latch + typed condition dispatch
**Path/Symbol:** `tracker/tracker/src/main/modules/conditionsManager.ts` — `trigger` (:102–110), `processMessage` (:112–134), operator table (:309–321), `mapCondition` (:323–436), duration ticker (:152–164), network sub-condition AND-fold (:166–206).
**Signature:** `processMessage(message: Message)`; `trigger(conditionName: string)` → `app.start(startOpts, undefined, name)`.
**Data Shape:** conditions from `/v1/web/conditions/<project>`: `{capture_rate, filters[{operator,value[],type,source}]}`; types map to click / visited_url / custom_event / exception / feature_flag / session_duration / network_request (sub-conditions on url/status/method/duration).

### Decisive source
```ts
trigger(conditionName: string) {
    if (this.hasStarted) return      // one-way latch
    this.hasStarted = true
    void this.app.start(this.startParams, undefined, conditionName)
}
...
const validSubConditions = reqCond.subConditions.filter((c) => c.operator !== 'isAny')
if (validSubConditions.length) {
  const allPass = validSubConditions.every(...)   // AND across url/status/method/duration
```

**Flow:** coldStart fetches conditions with the do-not-record token → every buffered message is dispatched by type → matching condition fires `trigger` once (latch) → start carries the condition name so the server applies its capture-rate dice instead of global sampling. Duration conditions run a 1 s interval checking `performance.now()`; stop callback clears it.
**Invariant:** `isAny` sub-conditions are filtered OUT of the AND set; if ALL are isAny, the condition auto-triggers. Latch must be set synchronously BEFORE async start to prevent duplicate sessions.
**Probe:** `grep -c 'hasStarted = true' tracker/tracker/src/main/modules/conditionsManager.ts` → `1`; `grep -c 'isAny' tracker/tracker/src/main/modules/conditionsManager.ts` → `2`; direct test suite `tests/conditionsManager.test.ts` executed green (339/339 full run).
**Coverage:** clean.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "openreplay", query: "ConditionsManager trigger processMessage mapCondition operators", limit: 10 });
```

## Verdict
Adopt latch-before-start and isAny semantics. Adapt operator vocabulary. Omit feature-flag source if you have no flag service.
