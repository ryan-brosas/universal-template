<!-- capsule-v2 -->
# Zero-overhead stage profiler — how do you add per-phase timing to hot query paths that costs nothing when disabled?

**Source:** nocodb (Sustainable Use License) `develop@640fe3b06f`; Codebase Memory `mnt-hdd-utopia-inspo-platforms-nocodb`. **Question:** What makes `timer?.mark()` free in production, and what does the emitted breakdown line look like?

## Null-timer factory + hrtime delta marks
**Path/Symbol:** `packages/nocodb/src/helpers/stageTimer.ts:StageTimer` (whole 84L); consumer: `src/db/BaseModelSqlv2.ts` (StageTimer.start around execAndParse).
**Signature:** `static start(label): StageTimer | null`; `mark(stage)`, `set(key, value)`, `totalMs(): number`, `toJSON()`, `end(logger?)`.
**Data Shape:** PERF_LOG_ENABLED = NC_PERF_LOG==='true' || !!ENABLE_PROFILER; stages Array<[name, ms]>; meta Record<string|number|boolean>.

### Decisive source
```ts
// When disabled, {@link StageTimer.start} returns `null` so every
// `timer?.mark()` / `timer?.end()` collapses to a cheap null check —
// effectively zero overhead in production.
static start(label: string): StageTimer | null {
  return PERF_LOG_ENABLED ? new StageTimer(label) : null;
}
...
// info level: NC_PERF_LOG is an explicit opt-in, so the breakdown should
// surface regardless of the global (pino) debug level being off.
logger.log(`${this.label} total=${total}ms ${stages}${meta ? ` | ${meta}` : ''}`);
```
(:9–:11, :36–:38, :78–:81)

**Flow:** call sites do `const timer = StageTimer.start('execAndParse')` once, then sprinkle optional-chained marks between phases (dbQuery/attachment/date/user/json/substitute) and set() context (rows/client/cacheHit) → end() emits ONE structured line `[Perf] <label> total=Xms s1=a s2=b | rows=N client=mssql` via logger.log at INFO regardless of global debug level; toJSON() exposes the same map for response `stats` blocks.
**Invariant:** the null-factory is the whole performance story — instrumentation must never branch on PERF_LOG_ENABLED at call sites or it leaks config coupling; private constructor + static start enforce it. mark() measures deltas since the LAST mark (not start), so phases tile the timeline. end() defaults to the module perfLogger but accepts one for tests.
**Probe:** `cd packages/nocodb && grep -c "PERF_LOG_ENABLED" src/helpers/stageTimer.ts` (=2: export decl + start() gate; doc-comment references it by name in prose only via {@link}) and `grep -c "hrtime.bigint" src/helpers/stageTimer.ts` (=3).
**Direct test:** none upstream — grep probes pin shape.

## Get live surrounding code
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-nocodb", query: "StageTimer start mark end PERF_LOG_ENABLED", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the null-timer factory + delta marks + single-line emission; adapt phase vocabulary to your pipeline; omit if APM tracing already covers per-phase latency. Coverage caveat: grep-pinned only.
