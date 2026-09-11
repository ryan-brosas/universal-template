<!-- capsule-v2 -->
# Grep-filtered pre-registration + locationPath identity — why does the reporter pre-register ALL matching tests at 'start', and what string IS a test's identity?

**Source:** JetBrains IDE installed build `WebStorm 262.9437.145` (mocha-intellij, cluster-identical); Codebase Memory `jetbrains-webstorm`. **Question:** How does the IDE get an instant full test tree with correct counts even before any test runs — and what key does the IDE use to navigate from a result to source?

## Start-time census under _grep
**Path/Symbol:** `plugins/nodeJS/js/mocha-intellij/lib/mochaIntellijReporter.js:296-317` (`runner.on('start')`: enteredTheMatrix → testingStarted → `treeUtil.forEachTest(runner …)` collecting tests where `runner._grep.test(test.fullTitle())` → `testCount count='N'` → registerTestNode for each); `mochaTreeUtil.js` (getRoot/findRoot/processTests recursive walk :4-39); identity = `getLocationPath` (:46-57 reporter + base variant in intellij-util.js:116-126 stopping at the FILE node).
**Signature:** `registerTestNode(tree, test): TestNode` — throws "Test node has already been associated!" on double registration; association stored ON the mocha objects as OWN properties `intellij_test_node` / `intellij_suite_node` (`hasOwnProperty`-guarded reads).
**Data Shape:** locationPath = dot-joined ancestor suite names (+ file path segment in the shared variant), delimiter-escaped with backslash; `locationHint = <nodeType>://' + locationPath`; metainfo carries the test FILE.

### Decisive source
```js
treeUtil.forEachTest(runner, function (test) {
  var match = true;
  if (runner._grep instanceof RegExp) {
    match = runner._grep.test(test.fullTitle());   // pre-filter by --grep
  }
  if (match) { tests.push(test); }
});
tree.writeln("##teamcity[testCount count='" + tests.length + "']");
tests.forEach(function (test) { registerTestNode(tree, test); });
// mochaTreeUtil association — own-property, not prototype:
function getNodeForTest(test) {
  if (hasOwnProperty.call(test, INTELLIJ_TEST_NODE)) return test[INTELLIJ_TEST_NODE];
  return null;
}
```

**Flow:** run start → walk the WHOLE mocha graph once → grep-filter → emit total count (IDE shows progress denominator) → register every node (IDE renders non-spinning placeholders) → as execution reaches each test its node merely flips to STARTED (no discovery latency).
**Invariant:** registration is one-shot per mocha object (own-property marker, double-register throws); late-discovered tests (not present at start) are still handled — `startTest` falls back to `registerTestNode` when unmarked (:105-112). Wrong port: registering WITHOUT the grep filter (counts and tree show excluded tests), or keying nodes by title alone across suites (collisions — hence hierarchical locationPath).
**Probe:** executed live via node v26.7.0 battery `/tmp/jb-p7/probe-v3.js`: Seq A asserts `testCount count='2'`, both pre-registered `running='false'` init messages BEFORE any start, and exactly ONE such message per pre-registered test.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-webstorm", query: "registerTestNode forEachTest", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt start-time census + pre-registration for instant-tree UX, and hierarchical escaped locationPath as the navigation identity. Adapt the filter predicate to your runner's filter primitive. Omit the metainfo=file convention only if your IDE side doesn't consume it.
