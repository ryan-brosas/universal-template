<!-- capsule-v2 -->
# Config normalization — how does a flat config array merge defaults, validate per-file, and produce the runtime `Config` object?

**Source:** ESLint MIT `main@dc1e7a8416937edefe04cf836ee202a6fc03bedd`; Codebase Memory project `eslint`. **Question:** How do you turn an array of user config objects into one validated, rule-resolved config for a file?

## FlatConfigArray layering + error localization
**Path/Symbol:** `lib/config/flat-config-array.js:FlatConfigArray` (:80–215).
**Signature:** `new FlatConfigArray(configs, { basePath, shouldIgnore=true, baseConfig=defaultConfig })`; `normalizeSync()`.
**Data Shape:** array layout after construction: `[...baseConfig, ...originalConfigs]`; symbols `originalLength`/`baseLength` record the boundary so errors can be localized to base / original / user-defined index.

### Decisive source
```js
this[originalLength] = this.length;
if (baseConfig[Symbol.iterator]) { this.unshift(...baseConfig); } else { this.unshift(baseConfig); }
this[baseLength] = this.length - this[originalLength];
// normalizeSync catches ConfigError and rethrows via wrapConfigErrorWithDetails:
// `${error.message.slice(0, -1)} at ${location} index ${configIndex}.`  // location ∈ base|original|user-defined
```

**Flow:** construct → unshift base config (defaults: language `js/js`, `@` plugin) → `normalizeSync()` validates each entry against `flatConfigSchema`, merges compatible entries, and finalizes each through `[ConfigArraySymbol.finalizeConfig] = config => new Config(config)`; `preprocessConfig` strips global-ignores-only entries when `shouldIgnore:false`.
**Invariant:** error indices are rebased (`error.index < baseLength ⇒ "base"` etc.) — a porter who reports raw indices blames the user for ESLint's own default-config bugs. Global ignores are recognized as entries whose only non-meta key is `ignores`.
**Probe:** `tests/lib/config/flat-config-array.js` (index rebasing, global-ignores stripping).

## Config resolution rules
**Path/Symbol:** `lib/config/config.js:Config` (:433–801) — constructor (:450–556), `#normalizeRulesConfig` (:608–633), `validateRulesConfig` (:647–766).
**Signature:** `getRuleDefinition(ruleId)`, static `getRuleOptionsSchema(rule)`, static `getRuleNumericSeverity(ruleConfig)`.

### Decisive source
```js
// #normalizeRulesConfig — every rule value becomes [numericSeverity, ...options]:
ruleConfig[0] = severities.get(ruleConfig[0]);            // "off"|"warn"|"error"|0|1|2 -> number
const mergedOptions = deepMergeArrays(rule?.meta?.defaultOptions, slicedOptions);
// validateRulesConfig — disabled rules skip validation entirely:
if (ruleOptions[0] === 0) continue;
const validateRule = getOrCreateValidator(rule, ruleId);   // ajv.compile cached in WeakMap by rule object
if (validateRule) validateRule(ruleOptions.slice(1));
```

**Flow:** schema-validate keys → require `language` and resolve it from the plugin's `languages` map (string→object) → merge `defaultLanguageOptions` under file `languageOptions` → normalize+validate every enabled rule against its compiled JSON-schema (`meta.schema:false` opts out; missing meta ⇒ no-options schema `{type:"array",minItems:0,maxItems:0}`) → apply `meta.defaultOptions` deep-merge.
**Invariant:** validation runs at config-construction time, before any linting — a porter who defers it produces mid-run crashes instead of actionable config errors. Rule IDs parse as `pluginName/ruleName` (scoped packages split on *last* slash; bare ids belong to the `@` core plugin). Severity lookup is case-insensitive strings or numbers, anything invalid ⇒ 0 (treated off).
**Probe:** `tests/lib/config/config.js` (schema forms, severity normalization, unsupported-language gate).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "eslint", query: "FlatConfigArray Config validateRulesConfig normalizeSync", limit: 10, fields: ["signature", "name", "file"] });
await mcp.codebase_memory.get_code_snippet({ project: "eslint", qualified_name: "eslint.lib.config.config.Config" });
```

## Verdict
Adopt base-config unshift + error-index rebasing, eager rule validation with WeakMap-cached validators, and numeric-severity normalization; adapt the schema library (ajv) and plugin map shape to host; omit TS/Bun/Deno config-file loading branches unless porting the loader too.
