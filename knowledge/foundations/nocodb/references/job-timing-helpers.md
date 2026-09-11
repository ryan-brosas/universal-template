<!-- capsule-v2 -->
|# hrtime stopwatch — dual-clock split timing for batch jobs

**Source:** nocodb (Sustainable Use License, develop branch) `develop@f751366`; Codebase Memory project `nocodb`. **Question:** How do you instrument multi-phase background jobs with split timings without a metrics dependency — and what does the lap contract require from callers?

## Path/Symbol
`packages/nocodb/src/modules/jobs/helpers.ts:initTime` (11–16), `elapsedTime` (18–38); consumers data-export.processor.ts:50/248-253, data-import.processor.ts:179/265-271, duplicate.processor.ts:111+.

**Signature:** `initTime(): NocoHrTime` where `NocoHrTime = {hrTime: [number,number]; totalHrTime: bigint}`; `elapsedTime(time, label?, context?)`.

**Data Shape:** dual anchors — `hrTime` (relative pair, per-lap) + `totalHrTime` (bigint epoch, cumulative). Output via `debug('nc:jobs:timings')`: `"<label>: <s>s <ms>ms; t=<total>s"` with channel suffix `JOBS_QUEUE:<context>` (`'exportData'`, `'fileImport'`, …).

### Decisive source
```ts
export const elapsedTime = (time: NocoHrTime, label?: string, context?: string) => {
  const elapsedS = process.hrtime(time.hrTime)[0].toFixed(3);      // lap via relative pair
  const elapsedMs = process.hrtime(time.hrTime)[1] / 1000000;
  const totalS = (process.hrtime.bigint() - time.totalHrTime)      // total via bigint delta
    / BigInt(1000) / BigInt(1000) / BigInt(1000);
  if (label) debugLog(`${label}: ${elapsedS}s ${elapsedMs}ms; t=${totalS}s`, ...);
  time.hrTime = process.hrtime();   // ← MUTATES the caller's struct
};
```

**Flow:** phase start → initTime once → after each phase call elapsedTime(t, label, context) → logs the split + running total → `time.hrTime` re-anchored, so consecutive calls chain laps without recreating the struct. Processors pass ONE object through whole jobs.

**Invariant:** (1) Lap = read + report + RE-ANCHOR as one side-effectful operation; splitting them invites double-counting or zero-length laps. (2) Lap and total use DIFFERENT representations (relative pair vs bigint nanoseconds) — mixing them is the classic porting bug. (3) Re-anchor even when logging is disabled: silent laps still advance. (4) Zero dependencies by design — debug-channel namespacing replaces any metrics client.

**Probe:** no unit test upstream. Source-grounded probe: helpers.ts whole file (38 L); consumer labels verbatim at data-export.processor.ts:248-253 and data-import.processor.ts:265-271.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "initTime elapsedTime NocoHrTime hrtime bigint", limit: 8, fields: ["signature","name","file"] });
```

## Verdict
Adopt the self-reanchoring dual-clock stopwatch with debug-channel logging; adapt the time source per runtime; omit nothing. Coverage caveat: no in-repo unit tests; source-grounded.
