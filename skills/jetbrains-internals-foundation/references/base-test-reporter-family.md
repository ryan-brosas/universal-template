<!-- capsule-v2 -->
# Base-test-reporter async family (intellij-tree.js) — what does the SHARED tree library add over the mocha-private one, and how do jest/vitest/node:test/protractor reuse it?

**Source:** JetBrains IDE installed build `WebStorm 262.9437.145`; Codebase Memory `jetbrains-webstorm`. **Question:** Five different test frameworks report into the IDE — what is the common reusable core and what does each framework adapter still own?

## One tree library, five adapters
**Path/Symbol:** shared kernel = `plugins/javascript-plugin/helpers/base-test-reporter/` (`intellij-tree.js` 774L Tree/Node/TestSuiteNode/TestNode + `sendMessage(key,value)` generic command emitter :73-80, `updateRootNode` rootName rename :46-56, `addTotalTestCount` :58-62; `intellij-util.js` 239L: `createWriter` :177-188, `AsyncSocketWriter` promise-chained writes :134-175, `getTestLocationPath` :116-126, `safeAsyncFn` :79-87). Consumers (relative requires or `_JETBRAINS_BASE_TEST_REPORTER_ABSOLUTE_PATH` env): vitest reporter + v3-plus + connector, jest-intellij reporter/jasmine2, nodejs-test-runner-intellij TestTreeBuilder, protractor-intellij (older private copy).
**Signature:** `new Tree(idPrefix: ?string, write: (s)=>void, rootId?: number|string)`; `tree.sendMessage(commandName, parameters: Record<string,string>)`.
**Data Shape:** adapters own ONLY framework event mapping; ids may be prefixed per worker (`<idPrefix>-<n>`), lookupMap values become ARRAYS on duplicate names with suite-preferred resolution.

### Decisive source
```js
// intellij-util.js — transport selection: env-declared socket else stdout
function createWriter(customSyncWrite) {
  if (!customSyncWrite) customSyncWrite = process.stdout.write.bind(process.stdout);
  const socket = maybeOpenSocket();          // JB_TEAMCITY_SOCKET_PATH | JB_TEAMCITY_SOCKET_PORT(+HOST)
  return socket ? new AsyncSocketWriter(socket) : new SyncWriter(customSyncWrite);
}
// AsyncSocketWriter: every write chains onto this._lastPromise; flush() awaits ALL pending
this._lastPromise = messagePromise; this._buffer.push(messagePromise);
// jest stdin-fix pre-hook (jest-intellij-stdin-fix.js):
process.stdout._intellijOriginalWrite = process.stdout.write.bind(process.stdout);
```

**Flow:** adapter process starts → `startNotify()` (`enteredTheMatrix`) → framework events → adapter builds nodes via `addTestSuiteChild/addTestChild` + `getTestLocationPath` → `writer.flush()` after EVERY callback (async family) → `testingFinished` + `writer.close()`.
**Invariant:** locationHint paths are built by joining ancestor names down to the FILE node (delimiter `.`, backslash-escaped) — navigation depends on file node being the stop node; socket mode MUST preserve write ORDER (promise chaining), stdout fallback must use the ORIGINAL write captured before jest's DefaultReporter wraps it.
**Probe:** executed live via node v26.7.0 battery `/tmp/jb-p7/probe-v3.js`: duplicate-name array collapse + suite preference; `findChildNodesByName` returns both; idPrefix applied; outcome double-set throws; skipped/failed message synthesis ("Skipped test 'y'" / "Failure cause not provided for 'x'").
**Coverage caveat:** protractor ships its own older tree copy (`protractor-intellij-tree.js`, 649L) — treat as frozen fork, not part of the shared contract.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-webstorm", query: "AsyncSocketWriter createWriter", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the split: ONE shared tree/writer/escaping kernel + thin per-framework adapters owning only event mapping — that is the porting architecture. Adapt writer selection to your transport. Omit jest-specific jasmine2 injection (see jest-jasmine2-injection capsule).
