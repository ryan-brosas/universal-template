<!-- capsule-v2 -->
# Diff-attribute extraction ladder (expected/actual) — when does a failure carry diffable expected/actual, and who stringifies them?

**Source:** JetBrains IDE installed build `WebStorm 262.9437.145` (mocha-intellij reporter + vitest/jest adapters); Codebase Memory `jetbrains-webstorm`. **Question:** Assertion libraries attach `expected`/`actual` in raw form — what gates decide whether the IDE receives a diff payload at all?

## showDiff gate + primitive passthrough + message-dedup veto
**Path/Symbol:** `plugins/nodeJS/js/mocha-intellij/lib/mochaIntellijReporter.js:165-185` (`getOwnProperty(err,'expected'/'actual'/'expectedFilePath'/'actualFilePath')`; gate `err.showDiff !== false && expected !== actual && expected !== undefined`; primitives `.toString()` "in compliance with mocha's own behavior" pinned to mocha v3.0.2 base.js URL comments :171-173, else `stringifier.stringify`); shared stringifier `mocha-intellij-stringifier.js` (mocha-utils stringify → deep-copy-and-normalize failover: sorted keys, `[Circular reference found] Truncated by IDE`, RegExp→source, bigint→string via replacer, final 'Oops, something went wrong…' fallback); vitest side dedup veto `vitest-intellij-util.js:281-285`; jest side `containsExpectedAndActualValues` (:280-288).
**Signature:** `setOutcome(outcome, durationMillis, failureMsg, failureDetails, expectedStr, actualStr, expectedFilePath?, actualFilePath?)`.
**Data Shape:** finish-message extras emitted only for STRING values (isString-guarded): `expected='…' actual='…' [expectedFile='…' actualFile='…']`.

### Decisive source
```js
if (err.showDiff !== false && expected !== actual && expected !== undefined) {
  if (util.isStringPrimitive(expected) && util.isStringPrimitive(actual)) {
    // in compliance with mocha's own behavior   ← pinned to upstream commit
    expectedStr = expected.toString();
    actualStr = actual.toString();
  } else {
    expectedStr = stringifier.stringify(expected);
    actualStr = stringifier.stringify(actual);
  }
}
// vitest adapter — suppress IDE diff when the assertion message ALREADY shows it:
const duplicated = isString(failureMessage) && isString(expectedStr) && isString(actualStr)
  && failureMessage.endsWith("expected '" + actualStr + "' to equal '" + expectedStr + "'");
return !duplicated;   // printExpectedAndActualValues
```

**Flow:** fail event → own-property extraction (prototype-inherited values ignored) → triple gate → stringify branch by primitiveness → outcome carries both strings → finish message appends escaped attributes; adapters additionally VETO printing when the message already embeds the same pair.
**Invariant:** `showDiff:false` must suppress the payload entirely; identical or undefined expected never emits; circular structures cannot crash the run (failover stringifier catches everything). Wrong port: JSON.stringify-ing raw values without normalization (circulars throw; key order churns diffs), or always emitting expected/actual (double display in hosts whose messages already contain them).
**Probe:** executed live via node v26.7.0 battery `/tmp/jb-p7/probe-v3.js`: Seq B fail with `{expected:'a', actual:'b', showDiff:true}` produces `testFailed … expected='a' actual='b'`; base-Tree synthesis checks pin the surrounding setOutcome contract.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-webstorm", query: "showDiff stringifier expected actual", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the three-gate + primitive-passthrough + normalized-failover pipeline and the message-dedup veto. Adapt the exact veto suffix to your assertion library's phrasing. Omit expectedFile/actualFile unless your host supports binary/image diffs.
