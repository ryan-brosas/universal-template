<!-- capsule-v2 -->
# Legacy CLIEngine + standard-v16 hybrid — how do you honor `eslint-config-standard` when standard itself has NO "is this file ignored" API?

**Source:** JetBrains IDE installed build `WebStorm 262.9437.145`; Codebase Memory `jetbrains-webstorm`. **Question:** above.

## Two-engine constructor with eslint resolved FROM standard's tree
**Path/Symbol:** `plugins/javascript-eslint/languageService/eslint/bin/eslint-plugin.js`:`ESLintPlugin` ctor (:18-35), `invokeESLint` (:72-104), `findESLintPackagePath` (:142-152), `createEmptyResult` (:153-162).
**Signature:** sync era: `invokeESLint(args, additionalOptions?) -> Linter report object`; standard path uses `standardLinter.lintTextSync(content, {filename, fix?})`.
**Data Shape:** ctor consumes `state.standardPackagePath?`, `state.eslintPackagePath`, `state.packageJsonPath`, `extraOptions` arrives as a CLI OPTION STRING parsed by the USER eslint's own `lib/options`.

### Decisive source
```js
// Standard doesn't provide API to check if file is ignored (https://github.com/standard/standard/issues/1448).
// The only way is to use ESLint for that.
this.standardLinter = requireInContext(standardPackagePath, state.packageJsonPath);
eslintPackagePath = findESLintPackagePath(standardPackagePath, state.packageJsonPath);
…
var cliEngine = new this.cliEngineCtor(options);
if (cliEngine.isPathIgnored(requestArguments.fileName)) return createEmptyResult();
if (this.standardLinter != null)
  return this.standardLinter.lintTextSync(requestArguments.content, standardOptions);
return cliEngine.executeOnText(requestArguments.content, requestArguments.fileName);

function findESLintPackagePath(standardPackagePath, contextPath) {
  var resolvedStandard = requireResolveInContext(standardPackagePath, contextPath);
  var requirePath = toUnixPathSeparators(require.resolve("eslint", { paths: [resolvedStandard] }));
  var ind = requirePath.lastIndexOf("/eslint/");
  if (ind < 0) throw Error("Cannot find eslint package for " + requirePath);
  return requirePath.substring(0, ind + "/eslint/".length);
}
```

**Flow:** standard present ⇒ require IT in its own context AND resolve `eslint` FROM standard's resolved directory (`require.resolve("eslint", {paths})`) then slice back to the last `/eslint/` segment — guaranteeing version-compatible peers — ⇒ per request: CLIEngine answers ONLY the ignored-question; actual linting delegates to `standard.lintTextSync`; no-standard path parses `extraOptions` with the user's options module, translates (vendored eslintrc-era translator :170-192), appends `additionalRulesDirectory` to rulePaths, gates FileKind acceptance, then `executeOnText`.
**Invariant:** (1) ignore-decision and lint-execution may come from DIFFERENT packages — that split is the workaround for upstream issue #1448, cited in-source; (2) eslint-for-ignore must be resolved from STANDARD'S tree, not the shim's; the string slice fails LOUDLY if the layout changes; (3) empty results are a full typed object (`results/warningCount/fixableWarningCount/fixableErrorCount/errorCount/usedDeprecatedRules`) because the wire body IS the raw Linter report in this generation.
**Probe:** `node --check eslint-plugin.js` → OK; `grep -c lintTextSync` = 1 (executed). Adversarial note: graph trace_path falsely lists `findESLintPackagePath` as called from eslint-plugin-provider — whole-file read shows the provider never calls it; source wins (recorded in verification.md).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-webstorm", name_pattern: "^findESLintPackagePath$", limit: 5 });
// hit: bin.eslint-plugin.findESLintPackagePath @ eslint-plugin.js:142-152
```

## Verdict
Adopt resolve-peer-from-dependency's-tree when two packages must agree on a shared engine. Adapt the ignore/lint split to whatever capability your wrapped tool lacks — the pattern is "borrow the missing capability from the compatible peer, cite the upstream gap in a comment". Omit nothing here if you target pre-flat eslint: the empty-result OBJECT shape is part of this generation's wire contract.
