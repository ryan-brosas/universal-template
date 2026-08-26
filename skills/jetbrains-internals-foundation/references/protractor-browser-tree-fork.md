<!-- capsule-v2 -->
# Protractor multi-browser tree fork — how do you report parallel browser sessions into one test tree when the shared library doesn't exist yet?

**Source:** JetBrains IDE installed build `WebStorm 262.9437.145` (protractor-intellij helper, self-contained older generation); Codebase Memory `jetbrains-webstorm`. **Question:** Before base-test-reporter existed, how did the protractor adapter structure a per-browser test tree and stay crash-proof inside the browser's jasmine env?

## Browser node + safe delegating reporter
**Path/Symbol:** `plugins/javascript-plugin/helpers/protractor-intellij/lib/protractor-intellij-plugin.js` (:8-26 — resolves `browser.getProcessedConfig()` then `getCapabilities()`, node name = `(browserName||'unknown browser') + ' ' + (version||'')`, `tree.root.addTestSuiteChild(name,'browser',null)` then start); `lib/protractor-intellij-jasmine-reporter.js` — `createSafeDelegatingReporter` (:22-40: EVERY reporter method wrapped in try/catch → warn), `createdPatchedSpec` (:42-58: subclasses `jasmine.Spec` to registry-map result.id→disabled state), `tryAttachReporter` (:11-20: no-op unless global `jasmine.getEnv().addReporter` exists).
**Signature:** `tryAttachReporter(browserNode): boolean`; suite/spec handlers mirror jasmine events with `getLocationPath(name, parentSuiteNode, stopNode=browserNode)`.
**Data Shape:** one `browserNode` per capabilities tuple; all location paths stop AT the browser node (no file segment — protractor configs run whole suites per browser); duration via wall-clock `Date.now()` deltas.

### Decisive source
```js
function createSafeDelegatingReporter(reporter) {
  var safeReporter = {};
  for (var key in reporter) {
    var method = reporter[key];
    if (typeof method === 'function') {
      safeReporter[key] = (function (method) {
        return function () {
          try { return method.apply(reporter, arguments); }
          catch (ex) { warn(ex.message + '\n' + ex.stack); }   // NEVER propagate
        };
      })(method);
    }
  }
  return safeReporter;
}
```

**Flow:** onPrepare attaches a safe-delegating jasmine reporter under a per-browser node → spec lifecycle updates that subtree synchronously (this generation has NO async writer — plain stdout writes) → unexpected statuses append `\nUnexpected spec status:<status>` to the failure message rather than crashing.
**Invariant:** reporter exceptions must never break the test run they are observing (in-browser jasmine has no supervisor); unknown statuses degrade to FAILED-with-appended-note, not throw. Wrong port: letting reporter errors propagate (kills the user's suite for a reporting bug), or assuming file-level nodes exist.
**Probe:** deterministic source pins: `'unknown browser'` fallback string :21-25 of plugin.js; patched-Spec disabled-state registry pattern shared with the jest jasmine2 reporter (lineage evidence). No behavior battery (needs a live selenium grid) — recorded honestly.
**Coverage caveat:** this capsule documents the LEGACY fork; port the modern base-test-reporter family instead unless maintaining protractor integrations.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-webstorm", query: "protractor jasmine reporter browser", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the never-throw reporter wrapper and capability-derived browser grouping for any parallel-executor reporting. Adapt node naming to your grid metadata. Omit the private Tree fork — superseded by base-test-reporter.
