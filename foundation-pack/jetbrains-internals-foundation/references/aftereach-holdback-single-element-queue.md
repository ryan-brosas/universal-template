<!-- capsule-v2 -->
# SingleElementQueue afterEach hold-back — how do you delay "test finished" until the afterEach hook has had its chance to fail the test?

**Source:** JetBrains IDE installed build `WebStorm 262.9437.145` (mocha-intellij reporter, md5-identical across 7+ products); Codebase Memory `jetbrains-webstorm`. **Question:** Mocha runs `afterEach` AFTER emitting `pass` — how does the IDE-side reporter avoid reporting a pass that a failing afterEach hook then contradicts?

## The one-slot deferred terminal
**Path/Symbol:** `plugins/nodeJS/js/mocha-intellij/lib/single-element-queue.js` (whole file, 29L: `add`/`processAll`/`clear`); wired at `mochaIntellijReporter.js:291-293` (`finishingQueue = new SingleElementQueue(testNode => testNode.finish(false))`), held at `:143-154`, drained on every subsequent event (`test`:327, `pending`:332, `beforeEach-fail`:342, `beforeAll-fail`:346, `suite end`:356, `end`:363), and cancelled at `:145-153`.
**Signature:** `new SingleElementQueue(processor: (element) => void)`; `add(el)`, `processAll()`, `clear()`.
**Data Shape:** capacity ONE — `current` holds at most the latest unfinished test node; overflowing `add` force-processes the previous element with a stderr warning ("unexpectedly unprocessed element").

### Decisive source
```js
function finishTestNode(tree, test, err, finishingQueue) {
  if (finishingQueue != null) {
    const passed = testNode != null && testNode === finishingQueue.current
      && testNode.outcome === Tree.TestOutcome.SUCCESS;
    if (passed && err != null) {
      // do not deliver passed event if this test is failed now
      finishingQueue.clear();          // DROP the queued testFinished entirely
    } else {
      finishingQueue.processAll();     // flush previous holder BEFORE new outcome
    }
  }
  …
  if (finishingQueue != null) { finishingQueue.add(testNode); }  // hold, don't finish
  else                       { testNode.finish(false); }
}
```

**Flow:** `pass(t1)` → outcome SUCCESS set but finish QUEUED → next event arrives (`test t2`, another result, suite end) → queue flushes `finish(t1)` first → only then does the new event process. If instead `fail(t1, err)` arrives while the queued node is still this test AND its outcome was SUCCESS → `clear()` discards the pass; the subsequent failure path emits exactly one terminal (`testFailed`).
**Invariant:** a test node emits AT MOST ONE terminal command even when mocha fires pass→fail for the same test (the WEB-10637 double-report family — a `this.test.error(...)` raised after pass). Wrong port: finishing eagerly on `pass` (loses afterEach failures) or naively emitting both events (IDE shows ghost passes).
**Probe:** executed live via node v26.7.0 battery `/tmp/jb-p7/probe-v3.js` driving the REAL IntellijReporter through synthetic runner events — Seq A ordering `[lateStart(t1,running=true)] < [testFinished t1] < [testStarted t2]`; Seq B pass→fail(same test) yields ZERO `testFinished` and exactly one `testFailed` carrying `expected='a' actual='b'`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-webstorm", query: "SingleElementQueue finishTestNode", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the hold-one-terminal pattern for any runner whose hooks run after the pass verdict (mocha, jest jasmine2). Adapt drain points to your runner's event set. Omit the stderr-warning overflow path only if your host guarantees drains.
