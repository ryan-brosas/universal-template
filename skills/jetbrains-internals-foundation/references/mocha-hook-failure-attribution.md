<!-- capsule-v2 -->
# Mocha hook-failure attribution ladder — where does a "before all"/"before each" hook failure get reported when the framework fires `fail` with the HOOK as the test?

**Source:** JetBrains IDE installed build `WebStorm 262.9437.145` (mocha-intellij, cluster-identical); Codebase Memory `jetbrains-webstorm`. **Question:** When a suite-level setup hook fails, which node carries the error — the hook itself, the current test, or every sibling test?

## Title-prefix dispatch + fan-out
**Path/Symbol:** `plugins/nodeJS/js/mocha-intellij/lib/mochaIntellijReporter.js` — `isHook` (:216-218, `test.type === 'hook'`), `isBeforeAllHook`/`isBeforeEachHook` (:224-234, TITLE-PREFIX match `'\"before all\" hook'` / `'\"before each\" hook'`), `runner.on('fail')` branch (:340-353), `handleBeforeEachHookFailure` (:254-267), `markChildrenFailed` (:241-248).
**Signature:** `markChildrenFailed(tree, suite, cause: string)`; `handleBeforeEachHookFailure(tree, beforeEachHook, err)`.
**Data Shape:** before-all → hook node FAILED + each already-registered sibling test finished FAILED with `message = <hook.title> + ' failed'`; before-each → attributed to `ctx.currentTest`'s node if registered, else to the hook node itself.

### Decisive source
```js
runner.on('fail', function (test, err) {
  if (isBeforeEachHook(test)) {
    finishingQueue.processAll();
    handleBeforeEachHookFailure(tree, test, err);   // prefer ctx.currentTest
  } else if (isBeforeAllHook(test)) {
    finishingQueue.processAll();
    finishTestNode(tree, test, err);                // hook node carries it…
    markChildrenFailed(tree, test.parent,
      test.title + " failed");                      // …and EVERY child fails too
  } else {
    finishTestNode(tree, test, err, finishingQueue);
  }
});
function handleBeforeEachHookFailure(tree, beforeEachHook, err) {
  var done = false;
  var currentTest = getCurrentTest(beforeEachHook.ctx);
  if (currentTest != null) {
    var testNode = treeUtil.getNodeForTest(currentTest);
    if (testNode != null) { finishTestNode(tree, currentTest, err); done = true; }
  }
  if (!done) { finishTestNode(tree, beforeEachHook, err); }
}
```

**Flow:** `fail` event with `type==='hook'` → title-prefix classification → before-all: flush queue, report hook, walk `suite.tests` and force-finish every REGISTERED child (unregistered ones are skipped — they never started) → before-each: attribute to the interrupted test via `ctx.currentTest`, falling back to the hook node.
**Invariant:** a failing before-all must fail ALL tests of its suite (the user sees why nothing ran), and the synthetic cause string is the hook TITLE — not the error message (the error rides on the hook's own node). Wrong port: reporting only the hook (IDE shows an empty suite with one obscure entry), or failing children that were never registered (null-deref via `getNodeForTest`).
**Probe:** executed live via node v26.7.0 battery `/tmp/jb-p7/probe-v3.js`: Seq C emits `testFailed name='"before all" hook for outer' message='setup broke'` PLUS `testFailed t1/t2 message='"before all" hook for outer failed'`; Seq D routes a beforeEach error to `name='t1'` carrying the original `message='each broke'`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-webstorm", query: "isBeforeAllHook markChildrenFailed", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the attribution ladder (current-test → hook → fan-out children). Adapt the title-prefix sniffing to however your runner labels hooks. Omit mocha's `ctx.currentTest` internals if your runner exposes the current test directly.
