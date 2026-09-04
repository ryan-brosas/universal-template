<!-- capsule-v2 -->
# Linter response envelope & payload hygiene — which parts of a helper process's error surface stay API-stable across three linter generations?

**Source:** JetBrains IDE installed build `WebStorm 262.9437.145`; Codebase Memory `jetbrains-webstorm`. **Question:** above.

## Shared ESLintResponse envelope, duplicated verbatim x3
**Path/Symbol:** vocabulary `.../bin/eslint-api.js`:`ESLintResponse` (:7-10), `GetErrors`/`FixErrors`/`FileKind` (:13-23); envelope logic in all three `onMessage` implementations (eslint-plugin.js :36-56, eslint8-plugin.js :98-138, standard17-plugin.js :47-87); stripping in each `filterSourceIfNeeded`.
**Signature:** `onMessage(jsonString, writer)` — parse → dispatch `GetErrors`|`FixErrors`|error → `writer.write(JSON.stringify(new ESLintResponse(seq, command)))`.
**Data Shape:** body differs by generation: legacy = FULL Linter report object (results + errorCount/warningCount/fixable*/usedDeprecatedRules); eslint8/std17 = `{ results: [...] }` wrapper. Error fields: `response.error` string + `response.isNoConfigFile` boolean.

### Decisive source
```js
catch (e) {
  response.isNoConfigFile =
    "no-config-found" === e.messageTemplate                       // structured field (legacy CLIEngine era)
    || (e.message && containsString(e.message.toString(), "No ESLint configuration found")); // message TEXT (later engines)
  response.error = e.toString() + "\n\n" + e.stack;
}
// filterSourceIfNeeded (all three shims):
if (!this.includeSourceText) {
  body.results.forEach(r => { delete r.source; r.messages.forEach(m => delete m.source); });
}
```

**Flow:** JVM sends one JSON request per file batch → shim answers exactly one JSON response with mirrored seq/command → classification of 'project has no eslint config' travels as a FIRST-CLASS flag so the IDE can offer setup help instead of an error balloon → source text stripped unless explicitly requested, bounding stdio payload size regardless of rule count.
**Invariant:** (1) no-config detection must match BOTH error shapes — different eslint generations put the fact in different fields; dropping either arm breaks one supported range; (2) the block is duplicated VERBATIM in all three shims (`grep -c no-config-found` = 1 in each): duplication IS the stability mechanism — the envelope never changes, only bodies do; (3) unknown commands answer with an error string rather than throwing, keeping the process alive; (4) `delete x.source` mutation happens AFTER linting but BEFORE serialization — consumers needing source snippets must set includeSourceText at construction.
**Probe:** executed: grep no-config-found = 1 in each of the three shim files; live require of the bundled eslint-api.js returned exactly `{ESLintResponse, FileKind, FixErrors, GetErrors}`; adversarial name_pattern translateOptions returned the two twins as DISTINCT rows (no cross-file bleed).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-webstorm", query: "ESLintResponse FileKind", limit: 6 });
// hits: bin.eslint-api.ESLintResponse :7-10 (in-degree 3 — all three shims), FileKind Variable :17-23
```

## Verdict
Adopt a frozen response envelope + per-generation body adapters when wrapping a fast-moving tool behind a long-lived IPC protocol; classify the ONE error you can act on (no-config) structurally AND textually. Adapt the stripped-field list to your wire budget. Omit nothing from the dual-shape match if you support more than one major of the wrapped tool.
