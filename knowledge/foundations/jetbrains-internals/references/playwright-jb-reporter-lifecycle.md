<!-- capsule-v2 -->
# Playwright JB reporter lifecycle - how does a pull-based suite model feed a push-based tree UI?

**Source:** PhpStorm Light installed build PS-262.9421 (proprietary; cite-only); Codebase Memory `jetbrains-phpstorm-light`. **Question:** How do you open/close ancestor suites when the runner API only hands you test-scoped callbacks?

## reporting/playwright adapter family
**Path/Symbol:** `plugins/javascript-plugin/reporting/playwright/playwrightReporter.js:onTestBegin/onTestEnd/onEnd` (:43-95); `playwrightSuitNode.js:PlaywrightSuitNode` (:22-33); `playwrightTestStructure.js:startStep/finishStep` (:27-39).
**Signature:** Playwright Reporter API: `onBegin(config, suite)`, `onTestBegin(test)`, `onStepBegin/End(test,result,step)`, `onTestEnd(test,result)`, `onEnd(result)`, `printsToStdio()===true`.
**Data Shape:** Playwright suites carry `parent`, `suites[], tests[]`, `titlePath()`; file-level suites detected by `titlePath().length === 3` and switch protocol to `file`; steps need `step.location`.

### Decisive source
```js
onTestBegin(test) {
  var suitesToStart = [];
  while (suite !== undefined && suite.status === NotStarted) { suitesToStart.push(suite);
    suite = suite.nativeSuite.parent === undefined ? undefined : new PlaywrightSuitNode(...parent); }
  suitesToStart.reverse().forEach(s => this.testStructure.startSuite(s));   // outermost first
}
onTestEnd: interrupted -> RETURN (leave node unfinished; IDE marks interrupted)
           else finishTest + close ancestors while ALL their tests+suites are Finished
onEnd: globalErrors flushed to stderr BEFORE finishTesting (ordered via write-callback)
```

**Flow:** onBegin preregisters (kernel) → first onTestBegin lazily opens the ancestor CHAIN reversed (project before file) → steps emit `testStepStarted/Finished` with `id/line/column/file` attrs, duration ONLY on finish, unlocatable steps silently dropped → onTestEnd cascades closes bottom-up → onEnd drains queued global errors to stderr then testingFinished.
**Invariant:** the ancestor walk terminates on `parent === undefined` — a null parent CRASHES PlaywrightSuitNode (probe-discovered: my fixture used null and died at :25; real Playwright roots use undefined). Suite-close cascade must check BOTH tests and nested suites finished, or mid-tree branches close early.
**Probe:** executed end-to-end against shipped reporter with fake natives: transcript shows reversed lazy opens (`p1` id1 before `a.spec.js` id2, both anchored parentNodeId='0'), step pair with duration-on-finish only, skipme emitted as testIgnored, halt (interrupted) emitting NOTHING, cascade closing file then project after t1 passes, stderr-before-finishTesting ordering.
**Coverage caveat:** coverage no_recorded_issue (reporter + structure); no shipped tests.

## Get live surrounding code
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-phpstorm-light", query: "PlaywrightJBReporter onTestBegin suitesToStart", limit: 6 });
```

## Verdict
Adopt reversed-chain opening + finished-cascade closing for ANY callback-only runner API. Adapt the titlePath-length heuristics to your host's suite naming. Omit step support where the runner lacks locations. Keep the stderr-drain-before-terminal ordering — losing it truncates global errors in the IDE console.
