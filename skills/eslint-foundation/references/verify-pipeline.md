<!-- capsule-v2 -->
# Verify pipeline — how does a lint call normalize a flat config, pick per-file config, and route to processor vs plain verify?

**Source:** ESLint MIT `main@dc1e7a8416937edefe04cf836ee202a6fc03bedd`; Codebase Memory project `eslint`. **Question:** How do you port the entry path from raw text + arbitrary config to executed rules without breaking config reuse or suppression accounting?

## Linter.verify entry
**Path/Symbol:** `lib/linter/linter.js:Linter.verify` (:829–868).
**Signature:** `verify(textOrSourceCode, config, filenameOrOptions): LintMessage[]` (`filenameOrOptions` may be a plain filename string or an options object).
**Data Shape:** string|`SourceCode` text; config = object|array; already-normalized arrays are detected duck-typed (`Array.isArray && typeof getConfig === "function"`) — never `instanceof`, because bundlers duplicate the class.

### Decisive source
```js
let configArray = configToUse;
if (!Array.isArray(configToUse) || typeof configToUse.getConfig !== "function") {
  configArray = new FlatConfigArray(configToUse, { basePath: cwd });
  configArray.normalizeSync();
}
return this._distinguishSuppressedMessages(
  this._verifyWithFlatConfigArray(textOrSourceCode, configArray, options, true),
);
```

**Flow:** resolve options → coerce non-normalized config into a `FlatConfigArray` + `normalizeSync()` → `_verifyWithFlatConfigArray` → split messages vs suppressed into instance slots.
**Invariant:** an array carrying `getConfig()` is reused as-is (rebuilding would lose plugin instances); anything else is rebuilt against the linter's cwd. Suppressed messages are stored on the instance (`getSuppressedMessages()`), never silently dropped from the return.
**Probe:** `tests/lib/linter/linter.js` (verify normalization, `getConfig`-bearing passthrough, suppression distinction).

## Per-file config resolution + routing
**Path/Symbol:** `lib/linter/linter.js:Linter._verifyWithFlatConfigArray` (:1365–1421).
**Signature:** `_verifyWithFlatConfigArray(textOrSourceCode, configArray, options, firstCall=false)`.
**Data Shape:** filename defaults to `"__placeholder__.js"` when absent (configs match against it); returns early with one severity-1 "No matching configuration found" message if `getConfig(filename)` yields nothing.

### Decisive source
```js
const config = configArray.getConfig(filename);
if (!config) { return [{ ruleId: null, severity: 1, message: `No matching configuration found for ${filename}.`, line: 0, column: 0 }]; }
if (config.processor) {
  const disableFixes = options.disableFixes || !config.processor.supportsAutofix;
  return this._verifyWithFlatConfigArrayAndProcessor(textOrSourceCode, config,
    { ...options, filename, disableFixes, postprocess, preprocess }, configArray);
}
if (firstCall && (options.preprocess || options.postprocess)) {
  return this._verifyWithFlatConfigArrayAndProcessor(textOrSourceCode, config, options);
}
return this._verifyWithFlatConfigArrayAndWithoutProcessors(textOrSourceCode, config, options);
```

**Flow:** `getConfig(filename)` selects the merged per-file `Config` → processor present ⇒ chunked verify (with autofix disabled unless the processor declares `supportsAutofix`) → else options-based processors on first call only → else the plain verify core (`#flatVerifyWithoutProcessors` :979–1315: parse via ParserService → apply language/inline config → collect directives → runRules → applyDisableDirectives).
**Invariant:** processor-derived fixes are force-disabled when `supportsAutofix` is falsy — a porter who keeps user `disableFixes:false` here produces corrupt multi-block output. Recursive re-verification of changed code blocks resolves config again per block (filename/ext changed ⇒ new config), keeping virtual filenames non-absolute.
**Probe:** `tests/lib/linter/linter.js` (processor dispatch, `supportsAutofix` gating, no-config placeholder message).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "eslint", query: "Linter.verify _verifyWithFlatConfigArray", limit: 10, fields: ["signature", "name", "file"] });
await mcp.codebase_memory.get_code_snippet({ project: "eslint", qualified_name: "eslint.lib.linter.linter.Linter.verify" });
```

## Verdict
Adopt the duck-typed normalized-array reuse, the placeholder-filename config lookup, and the suppressed-message slot pattern; adapt the cwd/basePath plumbing and message wording to host; omit esm-bundler workarounds specific to ESLint's packaging. Coverage caveat: graph index excludes nothing relevant here (`no_recorded_issue` + `metadata_match` on `lib/linter/linter.js`).
