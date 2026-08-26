<!-- capsule-v2 -->
# Processor routing + recursive re-config — when does a file get preprocessed, and how do extracted code blocks resolve their OWN config (or keep the legacy path)?

**Source:** ESLint MIT `main@dc1e7a8416937edefe04cf836ee202a6fc03bedd`; Codebase Memory project `eslint`. **Question:** How do you route a file through preprocess→per-block lint→postprocess and decide per block whether to reuse or re-resolve configuration?

## _verifyWithFlatConfigArray + processor verify
**Path/Symbol:** `lib/linter/linter.js:_verifyWithFlatConfigArray` (:1365–1421), `_verifyWithFlatConfigArrayAndProcessor` (:878–969), `_verifyWithFlatConfigArrayAndWithoutProcessors` (:1325–1354), `verify()` entry (:829–868).
**Signature:** `verify(textOrSourceCode, config, filenameOrOptions?)`; routing decision lives in `_verifyWithFlatConfigArray(text, configArray, options, firstCall)`.
**Data Shape:** processor = `{preprocess, postprocess, supportsAutofix?}`; blocks are strings (legacy → current-config lint) or `{path, body, rawBody, physicalPath}` objects; `filterCodeBlock(blockFilename, body)` defaults to `.endsWith(".js")`.

### Decisive source
```js
// duck-typing guard: webpack bundling breaks instanceof, so a FlatConfigArray is
// recognized by shape — an array WITH a getConfig() method:
if (!Array.isArray(configToUse) || typeof configToUse.getConfig !== "function") {
  configArray = new FlatConfigArray(configToUse, { basePath: cwd });
  configArray.normalizeSync();
}
const filename = options.filename || "__placeholder__.js";   // config lookup needs A name
const config = configArray.getConfig(filename);
if (config.processor) {
  const disableFixes = options.disableFixes || !config.processor.supportsAutofix;
  return this._verifyWithFlatConfigArrayAndProcessor(text, config,
    { ...options, filename, disableFixes, postprocess, preprocess }, configArray);
}
if (firstCall && (options.preprocess || options.postprocess))  // options-based processors
  return this._verifyWithFlatConfigArrayAndProcessor(text, config, options);
```

**Flow:** per block: legacy string → lint with CURRENT config; object → filter check; then IF content or extension changed vs original (`text !== block.rawBody || extname differs`) re-enter full `_verifyWithFlatConfigArray` with `filename: block.path` so a `.md`-extracted `.js` block gets JS config recursively; else lint directly without processors. Message lists go back through `postprocess`. `slots.lastSourceCode` caching means a SourceCode passed in skips parsing but still gets scope analysis if `scopeManager === null`.
**Invariant:** `supportsAutofix:false` forces `disableFixes` for that file — autofix across preprocessing boundaries would corrupt mapping; recursion is keyed on CHANGED content/extension only, otherwise infinite re-config loops; placeholder filename exists because flat config matching cannot run on "".
**Probe:** `tests/lib/linter/linter.js` :10350+ processor suites (:10387 preprocessors, :10684 postprocessors incl. supportsAutofix gating and changed-content recursive resolution).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "eslint", query: "_verifyWithFlatConfigArrayAndProcessor filterCodeBlock getConfig placeholder", limit: 10, fields: ["signature", "name", "file"] });
await mcp.codebase_memory.get_code_snippet({ project: "eslint", qualified_name: "eslint.lib.linter.linter.Linter.verify" });
```

## Verdict
Adopt shape-based config-array detection, placeholder-filename lookup, and changed-content-gated recursion; adapt processor contract to your plugin API; omit options-based processors if you only support config-declared ones.
