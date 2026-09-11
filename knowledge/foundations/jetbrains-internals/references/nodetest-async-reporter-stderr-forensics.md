<!-- capsule-v2 -->
# node:test async-generator reporter + stderr forensics — how do you report a runner that streams events from an iterator, and recover failures when the crash produced NO test events?

**Source:** JetBrains IDE installed build `WebStorm 262.9437.145` (nodejs-test-runner-intellij helper); Codebase Memory `jetbrains-webstorm`. **Question:** Node's built-in test runner reports via async-iteration custom reporters and dies silently on syntax errors — what adapter shape captures both worlds?

## Start-stack replay + StderrCollector backward walk
**Path/Symbol:** `plugins/nodeJS/js/nodejs-test-runner-intellij/nodejsTestRunnerIntellijReporter.js` (:84-121 — `module.exports = utils.safeAsyncGeneratorFn(async function* (source) {…})`, `yield ''` after EVERY event = stdout protocol keepalive); `lib/test-tree-builder.js` — `_testsStartDataStack` push-on-start (:200-202), `_popLastDoneTestNode` replay-walk (:278-309: for each stacked start, find-or-create children BY NAME walking from the file node, last-in-stack is the test itself; duplicate-name suites create a FRESH sibling when previous is finished :299-302); `lib/file-nodes.js` (`getFor` auto-finishes the PREVIOUS file node on switch :50-53); `lib/stderr-collector.js` whole (117L).
**Signature:** `reporter(source: AsyncIterable<NodeTestEvent>): AsyncGenerator<string>`; `StderrCollector.tryToBuildError(): {failureMsg, failureDetails}|undefined`.
**Data Shape:** `test:start` carries only `{file?, name, nesting}` — pass/fail come later, so tree shape is reconstructed by NAME at completion time. `checkFiledTestFile` detects syntax-error files (`file == null || details.error.exitCode === 1`) where the FILE PATH rides in `name`; `fixFilepathFoLocation` strips the `file://` prefix Node ≥21 adds.

### Decisive source
```js
// stderr-collector.js — filter debugger noise, then walk BACKWARD into three buffers
const debuggerMessagesStarts = ['Waiting for the debugger to disconnect...',
  'Debugger listening on', 'For help, see: https://nodejs.org/en/docs/inspector',
  'Debugger attached.'];
// ^ anchored regexes ('^' + key) remove inspector chatter before parsing
let currentBuffer = bufferOrder.pop();            // [message, stacktrace, nodeVersion]
while (i--) {
  if (currentData.message === '\n') {             // bare-newline CHUNKS are section dividers
    if (currentBuffer.length === 0) break;
    currentBuffer = bufferOrder.pop();
  } else { currentBuffer.unshift(currentData.message); }
}
const failureMsg = (message.startsWith(testFilePath) ? 'at ' : '') + message;
```

**Flow:** reporter iterates `source` → start pushes intent, pass/fail pops and replays the ancestor chain by name against the file node → syntax-error file case fabricates a `'file'`-type node seeded from collected stderr instead of event data → build() closes file nodes then testingFinished.
**Invariant:** the three stderr buffers fill BACKWARD (unshift) separated by bare-newline chunks — earliest lines become failureMsg (a code frame starting with the file path gets `'at '` prefixed so IDEA console renders it as a clickable URL), middle becomes stacktrace, tail becomes node version (kept "to understand cases with new unsupported syntax in old Node versions"); debugger lines filtered by ANCHORED prefixes only. Wrong port: splitting on `\n` inside chunk messages (dividers arrive as separate chunks), or filtering unanchored (would eat legit output).
**Probe:** executed live via node v26.7.0 battery `/tmp/jb-p7/probe-v3.js`: fixture with divider chunks → `failureMsg.startsWith('at /p/a.test.mjs')` TRUE, code frame in message, `SyntaxError:` line in details, `Node.js v20.19.0` preserved as tail, 'Debugger attached.' filtered.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-webstorm", query: "StderrCollector tryToBuildError TestTreeBuilder", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the async-generator reporter shape with per-event yield keepalives and the name-replay tree reconstruction for streaming runners; adopt the backward-buffer stderr forensics for any runner that can die pre-event. Adapt buffer count/divider token to your runtime's output shape. Omit the `file://` strip on runtimes <21.
