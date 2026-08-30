<!-- capsule-v2 -->
# Deferred test-tree reconstruction via start-stack replay — how do you build a hierarchical test tree from an event source that only reports nodes AFTER they happen?

**Source:** JetBrains IDE installed build `WebStorm 262.9437.145` (proprietary distribution; study/reference use only); Codebase Memory `jetbrains-webstorm`. **Question:** When your event stream has no reliable before-events to hang nodes on (node:test custom reporters emit `test:start`/`test:pass` pairs you cannot pair ahead of time), what replay structure reconstructs hierarchy while handling same-name siblings and filtered phantom events?

## The start-stack + name-chain walk
**Path/Symbol:** `plugins/nodeJS/js/nodejs-test-runner-intellij/lib/test-tree-builder.js:278-309` (`TestTreeBuilder._popLastDoneTestNode`) + stack push sites `:196-205` (`startTest`) + `lib/file-nodes.js` (`FileNodes.getFor`, 68L whole-file).
**Signature:** `startTest(d)` pushes one start-data frame onto `_testsStartDataStack`; `passTest(d)`/`failTest(d)` call `_popLastDoneTestNode(d)`; `build()` finishes the trailing file node + emits `testingFinished`.
**Data Shape:** the stack holds ONE frame per enclosing level of the currently-running test (suite…suite→test); nodes are created LAZILY at pass/fail time, never at start time; a per-file suite cache (`getFor`) starts a new file node AND auto-finishes the PREVIOUS one on file switch.

### Decisive source
```js
this._testsStartDataStack.forEach((testStartData, index) => {
  const children = currentNode.findChildNodesByName(testStartData.name);
  const isLastInStack = index === lastElementIndex;
  if (children.length === 0) {
    // If no one test in the file is satisfied for a filter query,
    // Node.js test runner will send test:start and test:pass events with name as filepath.
    if (testStartData.name !== filePath) {          // WEB-63419 phantom-event guard
      currentNode = createTestNode(testFileNode, currentNode, isLastInStack, testStartData);
      currentNode.start();
    }
  } else {
    currentNode = children[children.length - 1];    // LAST match among same-name children
    if (currentNode.isFinished()) {                 // repeated sibling: rerun of same-name suite
      currentNode = createTestNode(testFileNode, currentNode.parent,
        currentNode.getType() === 'test', testStartData);
      currentNode.start();
    }
  }
});
this._testsStartDataStack.pop();
```

**Flow:** async-generator reporter consumes `test:start|pass|fail|stderr` → `test:start` pushes a frame → `pass/fail` replays the WHOLE stack top-down under the per-file suite: walk existing children BY NAME (taking the LAST match), create missing levels, treat a finished same-name node as a REPEATED sibling and spawn a fresh one instead of reusing it → the last stack level becomes the actual terminal node → `build()` closes the final file node.
**Invariant:** the stack pops exactly once per done-event (3 pop sites total, incl. error paths); `file://` prefixes (node ≥21) are stripped before any path comparison/location use (`fixFilepathFoLocation`); a syntax-error file surfaces because node:test puts the FILE PATH in `name` (`resolveTestFilepath(testData.file || testData.name)`) — and the WEB-63419 guard turns that same quirk into the phantom-filter skip rule: a start whose name equals the resolved file path creates NO node. Wrong port: eagerly creating nodes at `test:start` duplicates every retried/filtered test, and reusing a finished node merges two runs of the same suite name into one.
**Probe:** deterministic (no upstream spec ships for these helpers — honest caveat): `grep -c "WEB-63419" plugins/nodeJS/js/nodejs-test-runner-intellij/lib/test-tree-builder.js` → 1; `grep -c "_testsStartDataStack.pop()" test-tree-builder.js` → 3; `grep -c fixFilepathFoLocation test-tree-builder.js` → 2 (:130 def + :139 call).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-webstorm", query: "TestTreeBuilder passTest failTest", limit: 5, fields: ["signature", "name", "file"] });
```
(resolves `...nodejs-test-runner-intellij.lib.test-tree-builder.TestTreeBuilder.passTest` at :207-227 and `.failTest` at :232-272, ranks 1–2.)

## Verdict
Adopt: start-stack + lazy name-chain replay for ANY push-only/aggregate-only event source (CI logs, streaming reporters, post-hoc result feeds). Adapt event-type names and the file-node latch to your runner. Omit node-version quirks beyond the documented `file://` strip and the WEB-63419 phantom guard. Complements `nodetest-async-reporter-stderr-forensics` (adapter shell + stderr recovery) — that capsule owns the generator/keepalive/forensics plane; this one owns the tree-construction algorithm itself.
