<!-- capsule-v2 -->
# Cypress mocha event bridge - how do you report a runner that is secretly another runner?

**Source:** PhpStorm Light installed build PS-262.9421 (proprietary; cite-only); Codebase Memory `jetbrains-phpstorm-light`. **Question:** Where do file locations come from when the underlying engine's Test objects don't carry them?

## reporting/cypress adapter family
**Path/Symbol:** `plugins/javascript-plugin/reporting/cypress/cypressReporter.js:CypressReporter` (:10-57); `cypressTestNode.js:absoluteFilePath/duration` (:30-50); `cypressUtils.js:fixIfWindowsFilePath` (:9-15).
**Signature:** `new CypressReporter(mochaRunner)` — Cypress IS mocha underneath, so the adapter subscribes to `Runner.constants` events directly.
**Data Shape:** location lives at `nativeTest.invocationDetails.absoluteFile` (Cypress-specific), NOT on the mocha test; duration may be undefined mid-run.

### Decisive source
```js
.on(EVENT_TEST_BEGIN, function (test) {
  test[TEST_STARTED_TIMESTAMP_INDEX] = performance.now();   // fallback duration stamp
  ...
})
get duration() { return this.nativeTest.duration != undefined ? ... : Math.round(performance.now() - stamp); }
get absoluteFilePath() { return this.nativeTest.invocationDetails.absoluteFile ?? ""; }
message.replace(/[\u001b\u009b][[()#;?]*(?:[0-9]{1,4}(?:;[0-9]{0,4})*)?[0-9A-ORZcf-nqry=><]/g, '')  // ANSI strip
```

**Flow:** EVENT_RUN_BEGIN walks `runner.suite` up to root → startTesting(root) preregisters; EVENT_TEST_PENDING pairs startTest + ignoreTest ("pending" = started then ignored); EVENT_TEST_FAIL finishes with normalizeError(err) which splits stack on message and strips ANSI codes; suites open lazily through the shared handler's guards.
**Invariant:** never trust the engine for fields it doesn't have — bridge layers must name WHERE each attribute really lives (invocationDetails for files, timestamp delta for durations). Windows paths arrive mixed-separator (`C:\Users\x/proj/e2e/`) and are normalized only when `:\\` is present.
**Probe:** executed: shipped cypressUtils.fixIfWindowsFilePath("C:\\Users\\dev/proj/e2e/x.cy.js") → all-backslash path; full fake-tree battery produced the exact TeamCity transcript cited in tc-eager-preregistration-kernel.
**Coverage caveat:** coverage no_recorded_issue for all four cypress files; no shipped tests.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-phpstorm-light", query: "CypressReporter EVENT_RUN_BEGIN invocationDetails", limit: 8 });
```

## Verdict
Adopt the attribute-source map (where each wire field truly originates) as THE deliverable of any bridge adapter. Adapt event-name tables per engine version. Omit ANSI stripping if your host already sanitizes output. The pending=start+ignore pairing ports unchanged to anything with a skipped state.
