<!-- capsule-v2 -->
# Time-scale nice with UTC detection — how do you "nice" a time scale by month/week/hour without corrupting UTC charts?

**Source:** visx (ui-visx) MIT `master@485c0359664ee8e612992defb16e1f035ed40b23`; Codebase Memory `ext-ui-visx`. **Question:** d3 `scaleTime.nice(interval)` needs a LOCAL time interval and `scaleUtc.nice` a UTC one — how do you pick correctly when you only hold an opaque scale?

## Probe the formatter, then choose the interval table
**Path/Symbol:** `packages/visx-scale/src/operators/nice.ts:applyNice` (:49–81) + `packages/visx-scale/src/utils/isUtcScale.ts:isUtcScale` (:11–16).
**Signature:** `applyNice(scale, config)`; `isUtcScale<Output>(scale: ScaleTime<Output,Output>): boolean`.
**Data Shape:** `config.nice` polymorphic: `true` → `scale.nice()`; `number` → tick count; `NiceTime` string (`'second'|'minute'|'hour'|'day'|'week'|'month'|'year'`) → interval table lookup; `{interval, step}` object → `table[interval].every(step)`.

### Decisive source
```ts
// isUtcScale.ts — the ONLY difference between time and utc scales
// is whether the tick format function is utcFormat or timeFormat
const output = scale.tickFormat(1, TEST_FORMAT)(TEST_TIME);
return output === '2020-02-02 03:04';
```
```ts
// nice.ts
const isUtc = isUtcScale(timeScale);
if (typeof nice === 'string') {
  timeScale.nice(isUtc ? utcIntervals[nice] : localTimeIntervals[nice]);
} else {
  const parsedInterval = (isUtc ? utcIntervals[interval] : localTimeIntervals[interval]).every(step);
  if (parsedInterval != null) { timeScale.nice(parsedInterval); }
}
```

**Flow:** boolean/number handled inline → object/string forms resolve the interval from the LOCAL or UTC table chosen by the probe result → `.every(step)` may return null, in which case nice is silently skipped (never throws).
**Invariant:** never call `timeScale.nice(utcInterval)` on a local-time scale (or vice-versa) — ticks shift by the TZ offset. The probe works because formatting is the single behavioral difference between the two scale types; when local time == UTC it always returns true (documented upstream).
**Probe:** `packages/visx-scale/test/utils/isUtcScale.test.ts` + `test/scaleTime.test.ts`/`test/scaleUtc.test.ts` (timezone-mock driven).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ui-visx", query: "applyNice utcIntervals", limit: 10, fields: ["signature", "name", "file"] });
// resolves packages/visx-scale/src/operators/nice.ts :49-81
```

## Verdict
Adopt the format-probe UTC detector + dual interval tables verbatim; adapt the `NiceTime` key set to your needs; omit the vendor re-export layer. Timezone tests are mock-driven — run them in your host TZ too if your app serves non-UTC users.
