<!-- capsule-v2 -->
# Vitest connector id-map + error normalization — how does the vitest adapter map task ids to tree nodes, and what must survive serialization into a readable failure?

**Source:** JetBrains IDE installed build `WebStorm 262.9437.145` (vitest-intellij helper); Codebase Memory `jetbrains-webstorm`. **Question:** Vitest hands the reporter whole task trees with serialized errors — what mapping and message/stack surgery makes them render correctly in the IDE?

## Three id maps + cause-chain stack builder
**Path/Symbol:** `plugins/javascript-plugin/helpers/vitest-intellij/vitest-intellij-reporter-connector.js` — maps `_filePathToFileNodeMap` (:63), `_suiteIdToSuiteNodeMap` (:68), `_testIdToTestNodeMap` (:73); `startTestingIfNeeded` lazy gate (:106-115); workspace file-node key `projectName + '|' + path` (:146) and display name `'|' + projectName + '| ' + basename` (:404-409); single-test-file scope REPLACES root via `updateRootNode` (:151-161). Error plane = `vitest-intellij-util.js` — `normalizeErrorFields` message/stack dedup (:112-142), `buildCauseErrorStack` walk (:148-171), cycle detection via object identity THEN 1-deep structural equality (:190-203), `getOutcome` matrix (:291-306), duration floor ad-hoc fix WEB-69673 (:59-62).
**Signature:** `normalizeError(error: SerializedError & {cause?}): {name, message, stack}`; `finishTestNode(testTask, testNode)`; `addErrorTestChild(parentNode, childName, failureMsg, failureDetails)`.
**Data Shape:** outcome: no result + mode skip/todo → SKIPPED; no result otherwise → ERROR; state pass → SUCCESS; else FAILED. Errors read `errors[0] ?? error`; suite hook children use beforeAll→FIRST error but afterAll→LAST error (beforeAll failure leaves two errors on the task).

### Decisive source
```js
function normalizeErrorFields(error) {
  …
  if (messageLines.length > 0 && stackLines.length > 0 && messageLines.length <= stackLines.length) {
    messageLines[0] = name + ': ' + messageLines[0]
    if (arrayEqual(messageLines, stackLines.slice(0, messageLines.length))) {
      message = messageLines.join('\n')
      stack  = stackLines.slice(messageLines.length).join('\n')   // strip duplicated prefix
    }
  }
  …
}
// cause chain → appended "Caused by:" blocks; cycle ⇒ label + prune
while (currentCauseError != null) {
  const isCycledCausedError = checkIsCycledCausedError(currentCauseError, handledErrors);
  stack += '\n' + (isCycledCausedError ? 'Cyclically caused by: ' : 'Caused by: ') + message;
  if (isCycledCausedError) { stack += '\n' + '    ...pruned stack due to a detected cycle'; break; }
  handledErrors.push(currentCauseError); currentCauseError = currentCauseError.cause;
}
```

**Flow:** vitest calls reporter callbacks → connector lazily starts testing on FIRST collection (`beforeTestingStart` latch, warns "Cannot finish not started testing" on premature finish) → tasks traversed depth-first creating suite/test nodes keyed by task id → `finishTestNode` normalizes error, stringifies expected/actual ONLY when different, sets `printExpectedAndActualValues=false` when the message already ends `expected '<actual>' to equal '<expected>'` (anti-duplication :281-285) → finish.
**Invariant:** task-id → node maps are cleared on every testing start (watch-mode reruns never resurrect stale nodes); cycled causes MUST terminate the walk (serialized vitest errors can repeat the same payload at several levels — WEB-75026). Wrong port: trusting `error.message` to include the error name (serialization drops it — the code re-prefixes `name + ': '`), or walking `cause` unguarded (infinite loop).
**Probe:** executed live via node v26.7.0 battery `/tmp/jb-p7/probe-v3.js`: `normalizeError({message:'top', stack:'Error: top\n at f', cause:{…root}})` → stack contains `Caused by: Error: root` + cause frames; self-referential `cause` → `Cyclically caused by:` + pruned marker.
**Coverage caveat:** upstream vitest types are pinned by URL comments; behavior probes cover the util plane, not the connector's full callback matrix.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-webstorm", query: "normalizeError buildCauseErrorStack", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the three-map identity scheme and the message/stack de-duplication + bounded cause-chain walk. Adapt the Angular-CLI sourcemap path repair (see angular-vitest-sourcemap-repair capsule). Omit coverage-config messaging (`vitest-coverage-config`) unless porting IDE coverage too.
