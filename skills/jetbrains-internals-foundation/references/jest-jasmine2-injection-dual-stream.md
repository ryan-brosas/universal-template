<!-- capsule-v2 -->
# Jest jasmine2 injection + dual-path reporting — how does the jest adapter self-install a per-file reporter inside workers, and reconcile two event streams for the same specs?

**Source:** JetBrains IDE installed build `WebStorm 262.9437.145` (jest-intellij helper); Codebase Memory `jetbrains-webstorm`. **Question:** Jest runs reporters in the MAIN process but tests in WORKERS — how does the adapter get live per-spec events without losing the main-process fallback?

## Config mutation at first test + stream dedup
**Path/Symbol:** `plugins/javascript-plugin/helpers/jest-intellij/lib/jest-intellij-reporter.js` — module-level singleton `tree`+`writer` (:5-8, top-level `startNotify()`), `configureJasmineReporter` (:47-80: mutates `test.context.config` to append the jasmine reporter via `setupFilesAfterEnv` (jest≥24) or legacy `setupTestFrameworkScriptFile`, saving the original into globals `_JB_INTELLIJ_ORIGINAL_SETUP_TEST_FRAMEWORK_SCRIPT_FILE`; automock guard pushes helper into `unmockedModulePathPatterns`; `transformIgnorePatterns` gains the helpers dir); runner gating `canConfigureJasmineReporter` (:89-100 — testRunner path must END `/jest-jasmine2/build/index.js`). Fallback plane = `jest-intellij-util.js` — `reportSpecResult` (:110-128) with duplicate guard (`mightBeDuplicate` for todo double-fire :115-118) and "first UNFINISHED node wins" resolution (:97-102, :121-125); status mapping `getOutcome` (:207-218: passed→SUCCESS; pending/disabled/todo→SKIPPED; else FAILED).
**Signature:** `onTestCaseStart/onTestCaseResult/onTestFileResult(test, …)`; jasmine side: `suiteStarted/suiteDone/specStarted/specDone(result)`.
**Data Shape:** worker (jasmine) path emits live nodes; main-process path rebuilds suites from `ancestorTitles` (`resolveSpecParent`) and reuses existing unfinished spec nodes by title; file nodes get `testFileNode.id = test.path` then register+start immediately.

### Decisive source
```js
// reporter.js onTestFileResult — reconcile both streams
testResults.forEach(function (testResult) {
  if (!reporterObj._onTestCaseResultCalled) {
    reportSpecResult(…)                                  // no live stream → rebuild from results
  } else if (testResult.status === 'todo' || testResult.status === 'pending') {
    reportSpecResult(…, mightBeDuplicate=true)           // todo double-fires across streams
  }
});
// util.js — same-name spec resolution
function findFirstUnfinishedSpecNode(parentNode, childName) {
  const specNodes = parentNode.findChildNodesByName(childName);
  return specNodes.find(specNode => !specNode.isFinished());
}
// jasmine2 reporter — per-file tree identity
const tree = new Tree(getUniqueTestFileRunId(), writer.write.bind(writer), testFilePath);
```

**Flow:** `onRunStart` resets state → FIRST test file start mutates its config to inject the jasmine reporter → in-worker jasmine events build the tree live (startAncestorSuites lazily opens suite chain) → main-process callbacks ALSO fire; adapter prefers the live stream and uses aggregated results only when `_onTestCaseResultCalled` is false, tolerating todo/pending double reports → `onRunComplete` finishes stragglers (`finishIfStarted`) then testingFinished.
**Invariant:** exactly one of the two paths may finish a given spec — unfinished-first lookup + duplicate flag prevent double terminals when both streams report the same title; `--testNamePattern` runs mark non-matching tests pending and MUST be dropped under suite/test scope (:111-113). Wrong port: blindly appending a second reporter entry (double events), or finishing specs from aggregated results while the live stream already did.
**Probe:** deterministic source pins: `'/jest-jasmine2/build/index.js'` suffix gate verbatim :93-94; `_JB_INTELLIJ_JASMINE_REPORTER_DISABLED` env kill-switch; `Symbol.for('$$jest-matchers-object')` testPath recovery (jasmine2 reporter :45-56). Behavior battery covers the shared Tree plane these calls ride on.
**Coverage caveat:** full jest worker pipeline needs jest itself (absent in install) — attribution/dedup logic verified by source inspection.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-webstorm", query: "configureJasmineReporter reportSpecResult", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the config-injection-at-first-opportunity pattern to move reporting INTO the worker process, plus the prefer-live/reconcile-aggregate rule. Adapt the jasmine2 suffix gate to your jest version. Omit the stdin-fix shim unless your host also wraps stdout.
