<!-- capsule-v2 -->
# Cucumber step-result TeamCity state machine — what does a step-level emitter's status ladder look like, and how are duplicate results suppressed?

**Source:** JetBrains IDE installed build `WebStorm 262.9437.145` (proprietary distribution; study/reference use only); Codebase Memory `jetbrains-webstorm`. **Question:** above.

## Status ladder + lastFailedTestName swallow
**Path/Symbol:** `plugins/javascript-cucumber/lib/cucumberjs_formatter_common.js`:`buildHandlers/handleStepResult` (:70-119); closure state `lastFailedTestName` (:58).
**Signature:** `handleStepResult(event, callback)` — async-callback style (cucumber v1/v2 formatter API).
**Data Shape:** status vocabulary: `skipped|pending → testIgnored`, `undefined → testFailed error='true' message='Undefined step: <name>'`, `failed → testFailed(with escaped stack) + customProgressStatus type='testFailed'`; EVERY branch falls through to a trailing `testFinished` with computed duration.

### Decisive source
```js
if (lastFailedTestName != null && lastFailedTestName === getName(step)) {
  callback();            // ENTIRE result swallowed — no ignore, no finish, no duration
  return;
}
lastFailedTestName = null;
...
} else if(getStatus(stepResult) === "failed") {
  lastFailedTestName = getName(step);          // arm the swallow for the NEXT same-named step
  ...
}
message = "##teamcity[testFinished ... duration = '%s' name = 'Step: %s']";   // always emitted
var duration = (stepResult.getDuration ? ... : stepResult.duration) || 0;
message = message.replace('%s', Math.round(duration / (useMilliseconds ? 1000 : 1000000)));
```

**Flow:** dedup check → status branch (emit ignore/fail messages) → unconditional testFinished → `callback()`. The failed branch arms `lastFailedTestName`; the NEXT StepResult whose step name equals it is dropped entirely, then the latch clears.
**Invariant:** every non-swallowed step produces exactly one terminal `testFinished`, so the IDE-side tree never sees a dangling started step; duration is normalized to milliseconds at emission (`|| 0` guards missing durations).
**Probe:** no upstream tests ship with the distribution. Executed live against the REAL module with synthetic events (console.log captured): failed step emitted `testFailed` (escaped stack) + `customProgressStatus type='testFailed'` + `testFinished duration='2'` from a 2000000 ns input with `useMilliseconds=false` (confirms the ns divisor), and an immediately following PASSED StepResult with the SAME step name produced ZERO additional messages (9 total captured, as predicted).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-webstorm", query: "buildHandlers", limit: 10 });
// rank-1: cucumberjs_formatter_common.buildHandlers :55-246; second row cucumberjs_formatter_v2 (caller)
```

## Verdict
Adopt the always-terminal-finish discipline and the millisecond normalization boundary. Adapt the swallow latch only with care: it is keyed on step NAME alone, so two distinct steps sharing a name lose one result — port it as a documented retry/duplicate guard, not a general dedup. Omit the hardcoded `diagnosticInfo` epoch constant (`f/s=(1344855950447,…)` — a frozen 2012 timestamp kept purely for IDE log cosmetics). Coverage caveat: no dedicated upstream spec drives this file; evidence is whole-source read plus executed probes.
