<!-- capsule-v2 -->
# FileKind acceptance gates — when must a linter host REFUSE to lint a file kind its config can't handle, decided WITHOUT running the linter?

**Source:** JetBrains IDE installed build `WebStorm 262.9437.145`; Codebase Memory `jetbrains-webstorm`. **Question:** above.

## Legacy heuristic sniff vs eslint8 html-only gate
**Path/Symbol:** `plugins/javascript-eslint/languageService/eslint/bin/eslint-plugin.js`:`isFileKindAcceptedByConfig(config, fileKind)` (:108-141) + nested `hasPlugin` (:110-113) / `hasParser` (:114-118); eslint8 twin gate in `invokeESLint` (:192-209).
**Signature:** legacy: `isFileKindAcceptedByConfig(config, "ts"|"html"|"vue"|"js_and_other") -> boolean` fed by `cliEngine.getConfigForFile(fileName)`; v8: `await eslint.calculateConfigForFile(fileName)` then plugin sniff, gated ONLY for `FileKind.html`.
**Data Shape:** empty-result duality on refusal: legacy returns the full typed object from `createEmptyResult()` (`{results:[],warningCount:0,fixableWarningCount:0,fixableErrorCount:0,errorCount:0,usedDeprecatedRules:[]}`); v8 returns bare `[]` because its wire body wraps results.

### Decisive source
```js
// legacy aliases encode HISTORY:
hasPlugin("typescript") || hasPlugin("@typescript-eslint")   // typescript plugin was later renamed
  || hasParser("babel-eslint") || hasParser("@babel/eslint-parser")
  || hasParser("typescript-eslint-parser") || hasParser("@typescript-eslint/parser")   // ts kind
hasPlugin("vue") || hasPlugin("html") || hasParser("vue-eslint-parser")
// ^ eslint-plugin-html processed .vue files prior to v5; eslint-plugin-vue alone sufficed prior to v3
// hasPlugin matches value OR "eslint-plugin-" + value; hasParser substring-matches normalizePath-ed config.parser / parserOptions.parser

// eslint8 flat-aware form:
hasHtmlPlugin = Array.isArray(plugins)
  ? plugins.includes("html")
  : Object.keys(plugins).some(p => p.toLowerCase().includes("html"));  // flat configs namespace plugins as OBJECT KEYS
```

**Flow:** request carries the JVM-side FileKind (values mirror `EslintUtil.FileKind`, see eslint-linter-shim-version-dispatch) → resolve the effective config FOR THAT FILE first (legacy sync `getConfigForFile`, v8 async `calculateConfigForFile`) → refuse with the generation's empty result when the config shows no plugin/parser capable of the kind; `js_and_other` is never gated (eslint core always applies).
**Invariant:** (1) the gate prevents FALSE SILENCE — without it a ts file hitting a js-only config yields zero errors that look like success; (2) alias lists are append-only history: old names must keep matching or old projects silently stop linting; (3) parser matching is SUBSTRING over normalized paths because configs reference parsers by relative and resolved paths inconsistently; (4) refusal shape MUST match the generation's body contract (object vs array).
**Probe:** executed retrieval rows resolve line-exact — hasPlugin :110-113, hasParser :114-118, isFileKindAcceptedByConfig :108-141; `grep -c calculateConfigForFile` = 1; `node --check` OK on both files.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-webstorm", query: "isFileKindAcceptedByConfig hasParser", limit: 6 });
// hits: bin.eslint-plugin.{isFileKindAcceptedByConfig :108-141, hasPlugin :110-113, hasParser :114-118}
```

## Verdict
Adopt capability-gating BEFORE invocation whenever a generic linter host multiplexes file kinds; derive the gate from resolved config, never from file extension alone. Adapt the alias tables to your ecosystem's rename history — treat them as compatibility contracts. Omit per-kind gating for the kind every config covers natively (plain JS here).
