<!-- capsule-v2 -->
# Vendored CLI-option translation, flat vs eslintrc — how do you turn a linter's CLI option string into constructor options across two config formats without importing its cli.js?

**Source:** JetBrains IDE installed build `WebStorm 262.9437.145`; Codebase Memory `jetbrains-webstorm`. **Question:** above.

## Forked translator with pinned upstream provenance
**Path/Symbol:** `plugins/javascript-eslint/languageService/eslint/bin/eslint8-plugin.js`:`translateOptions(cliOptions, configType)` (:233-347) + `normalizeSeverityToString(severity)` (:355-366); caller wiring :170-175.
**Signature:** `translateOptions(parsedCLIOptions, "flat" | "eslintrc") -> ESLintConstructorOptions`; `normalizeSeverityToString(0|1|2|"0"|"1"|"2"|"off"|"warn"|"error") -> "off"|"warn"|"error"\ (throws otherwise)`.
**Data Shape:** input = result of the USER eslint's own `lib/options.parse(extraOptions || "")` (a FACTORY call `libOptions(usingFlatConfig)` at eslint ≥8.23+, plain object before — probed via `parse instanceof Function`); output keys differ per branch.

### Decisive source
```js
if (configType === "flat") {
  overrideConfigFile = (typeof config === "string") ? config : !configLookup;
  if (overrideConfigFile === false) overrideConfigFile = void 0;
  globals = global.reduce((obj, name) => (name.endsWith(":true") ? obj[name.slice(0,-5)]="writable" : obj[name]="readonly", obj), {});
  overrideConfig = [{ languageOptions: { globals, parserOptions: parserOptions || {} }, rules: rule ? rule : {} }];
} else {
  overrideConfigFile = config;
  overrideConfig = { env: …{name:true}, globals: …writable/readonly, ignorePatterns, parser, parserOptions, plugins, rules };
}
// flat-only extras: options.ignorePatterns = ignorePattern; options.flags = flag;
// options.warnIgnored NOT set --- "not needed because the IDE doesn't lint ignored files; backward compatibility gets broken if uncommented"
```
Header comment pins provenance: `See https://github.com/eslint/eslint/blob/0dd9704c…/lib/cli.js#L69` — a FORK of eslint's private CLI translation, kept in-tree.

**Flow:** parse the extra-options CLI STRING with the user's own parser → translate under the request's config format → merge with per-request overrides ({fix:true} on FixErrors) → `overrideConfigFile` replaces legacy `configFile`; legacy-only knobs (rulePaths/useEslintrc/extensions/ignorePath/resolvePluginsRelativeTo) stay in the eslintrc branch; flat branch moves reportUnusedDisableDirectives into `linterOptions` after severity normalization.
**Invariant:** (1) the async parser/plugin CLI importers exist upstream but are COMMENTED OUT here — plugins/parsers flow through config FILES, never CLI flags, in this host; port that scope decision, not just the code; (2) `warnIgnored` omission is deliberate with an in-source reason comment; (3) globals keep the CLI convention `name:true ⇒ writable`; (4) severity normalization accepts number AND string spellings because different eslint versions emit different types.
**Probe:** `node --check eslint8-plugin.js` → OK; `grep -c overrideConfigFile` = 7, `grep -c calculateConfigForFile` = 1 (executed). Adversarial retrieval returns BOTH vendored twins as distinct rows (see below) — cite by qualified name, never by bare symbol.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-webstorm", name_pattern: "translateOptions", limit: 10 });
// hits: bin.eslint-plugin.translateOptions @ eslint-plugin.js:170-192 (eslintrc-era twin)
//       bin.eslint8-plugin.translateOptions @ eslint8-plugin.js:233-347 (dual-mode)
```

## Verdict
Adopt fork-with-provenance-comments when you need a dependency's private option translation but cannot import it; pin the exact upstream commit in the header comment. Adapt branch sets to the config generations you support. Omit upstream async importers deliberately and SAY SO in a comment — silent omission is what turns a fork into drift.
