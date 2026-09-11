<!-- capsule-v2 -->
# TC eager preregistration kernel - how do you give an IDE a complete test tree before any test has run?

**Source:** PhpStorm Light installed build PS-262.9421 (proprietary distribution; cite-only); Codebase Memory `jetbrains-phpstorm-light`. **Question:** How does a reporter hand the IDE the full suite shape up-front instead of streaming nodes as they start?

## TestEventsHandler + TestNode (plugins/javascript-plugin/reporting/core)
**Path/Symbol:** `plugins/javascript-plugin/reporting/core/testEventsHandler.js:TestEventsHandler.registerTestNodes` (:115-132) and `:startTesting` (:38-43); `core/testNode.js:TestNode.toKeyValueString/getLocationHint` (:48-64).
**Signature:** `new TestEventsHandler(write = console.log)`; `startTesting(rootSuite)`; `registerTestNodes(suite, parentNodeId): count`.
**Data Shape:** node state (`nodeId`, `parentNodeId`, `testNodeStatus`) is stored AS MAGIC FIELDS ON THE NATIVE framework element via the TestNode accessor; status enum NotStarted=0/Running=1/Finished=2. Messages are `##teamcity[…]` lines through injectable `write` (tests swap it for a capture fn).

### Decisive source
```js
startTesting(rootSuit) {
  this.write(teamcityFormatMessage("enteredTheMatrix"));
  this.write(teamcityFormatMessage("testingStarted"));
  var count = this.registerTestNodes(rootSuit, this.nextNodeId++);   // root CONSUMES id 0
  this.write(teamcityFormatCountMessage(count));                     // ##teamcity[testCount count='N']
}
// registerTestNodes: skips setUpTestNode for root, but children anchor on parentNodeId=0
```

**Flow:** enteredTheMatrix → testingStarted → recursive id assignment over suites+tests (root skipped as node but its pre-incremented id becomes every top-level node's `parentNodeId='0'`) → testCount → later per-event startSuite/startTest/finishTest(error?)/finishSuite → testingFinished. Every transition is guarded by status (idempotent double-start/double-finish are silent no-ops); root and non-Running nodes never emit.
**Invariant:** ids are position-independent — the IDE builds nesting from `parentNodeId`, so name duplicates are legal. Dots in `locationHint` are backslash-escaped ONLY when a dotted `locationInFile` follows the file path (`file:///a/b\.spec\.js.suite.test` vs plain `file:///a/b.spec.js`) — the source cites FileUrlProvider.java:78 for this asymmetry. Attribute escaping uses the pipe dialect (\n→|n, '→|', |→|| …).
**Probe:** executed from install root: fake Cypress-shaped tree driven through the SHIPPED classes → transcript shows `testCount count='2'` BEFORE any testStarted, `nodeId='2' parentNodeId='1'`, NaN duration while running, escaped `name='passes |'quotes|' || pipes'`, newline in details as `|n`.
**Coverage caveat:** check_index_coverage no_recorded_issue ×3 (core/testEventsHandler.js, core/testNode.js, core/reporterUtils.js); no shipped tests — behavior pinned by probe.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-phpstorm-light", query: "TestEventsHandler registerTestNodes teamcityFormatCountMessage", limit: 8 });
```
(line-exact hits on core/testEventsHandler.js observed this pass.)

## Verdict
Adopt eager registration + numeric parent anchors whenever the runner can enumerate its tree at start (better UX than lazy discovery). Adapt the magic-field state placement to your host's object ownership. Omit the mocha-specific event wiring (see cypress-mocha-event-bridge). Distinct from karma-teamcity-tree-wire, which streams a LAZY server-side tree — pick by whether you can walk the whole tree early.
