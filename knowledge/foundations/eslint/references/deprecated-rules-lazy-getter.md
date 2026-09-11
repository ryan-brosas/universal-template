<!-- capsule-v2 -->
# Deprecated-rules lazy getter — when is `usedDeprecatedRules` computed, why is it a lazy property, and why must it never enter the cache file?

**Source:** ESLint MIT `main@c27bc926e496985eb7911c09eb60914b2e4b5d0f` (tag v10.9.0); Codebase Memory project `eslint` (direct source+test fallback — graph not connected this session). **Question:** A porter must reproduce the lazy-attachment design and the Config-keyed memoization without leaking the array into persisted results.

## processLintReport / getOrFindUsedDeprecatedRules

**Path/Symbol:** `lib/eslint/eslint.js:processLintReport` (:195-209), `getOrFindUsedDeprecatedRules` (:147-186), `getDeprecatedRuleReplacements` (:115-133), module-level `usedDeprecatedRulesCache` WeakMap (:138-139).
**Signature:** `processLintReport(eslint: ESLint, results: LintResult[]): LintResult[]`; getter `usedDeprecatedRules: DeprecatedRuleInfo[]` where `DeprecatedRuleInfo = { ruleId, replacedBy: string[], info?: object }`.
**Data Shape:** `usedDeprecatedRulesCache: WeakMap<CalculatedConfig, DeprecatedRuleInfo[]>` — keyed BY CONFIG OBJECT, so memoized arrays die with their config (a strong Map would leak configs across ESLint instances).

### Decisive source

```js
	const descriptor = {
		configurable: true,
		enumerable: true,
		get() {
			return getOrFindUsedDeprecatedRules(eslint, this.filePath);
		},
	};

	for (const result of results) {
		Object.defineProperty(result, "usedDeprecatedRules", descriptor);
	}
```

```js
	if (config && !usedDeprecatedRulesCache.has(config)) {
		const retv = [];

		if (config.rules) {
			for (const [ruleId, ruleConf] of Object.entries(config.rules)) {
				if (Config.getRuleNumericSeverity(ruleConf) === 0) {
					continue;
				}
				const rule = config.getRuleDefinition(ruleId);
				const meta = rule && rule.meta;

				if (meta && meta.deprecated) {
					const usesNewFormat = typeof meta.deprecated === "object";

					retv.push({
						ruleId,
						replacedBy: getDeprecatedRuleReplacements(meta),
						info: usesNewFormat ? meta.deprecated : void 0,
					});
				}
			}
		}

		usedDeprecatedRulesCache.set(config, Object.freeze(retv));
	}
```

**Flow:** `processLintReport` runs LAST in both lintFiles and lintText tails and installs ONE getter descriptor per result (no computation at attach time). First ACCESS walks `config.rules` skipping severity-0 entries, collects `meta.deprecated` rules — `replacedBy` via `getDeprecatedRuleReplacements` (old format: `meta.replacedBy || []`; new format: mapped `plugin/rule` shorthand names, empty string for malformed entries; `info` present ONLY when `meta.deprecated` is an object) — and memoizes a FROZEN array in the WeakMap keyed by config ("most files use the same config"). Non-absolute `maybeFilePath` resolves through `getPlaceholderPath(cwd)`; unconfigured files ⇒ frozen `[]`.
**Invariant:** the property must be a getter (lazy), enumerable (JSON-serializable on access), and computed against the FINAL result set; the memo must be frozen and Config-keyed; the computed array must never be written into the lint-result cache file — the cache stores pre-decoration results, so a cached result re-gains the getter on every run (this is what keeps stale deprecation info out of persisted state).
**Probe:** `tests/lib/eslint/eslint.js` deprecated-rule info shape (:1230-1245 — deepStrictEqual with `info: coreRules.get("indent-legacy")?.meta.deprecated`) and "should not store `usedDeprecatedRules` in the cache file" across 3 consecutive runs (:14287-14356). Executed: within the 11-passing mocha subset (`usedDeprecatedRules|Normalized inputs|Invalid inputs|unknown key`). Executed live probe: `space-in-parens` config → `[{ruleId:"space-in-parens", replacedBy:["@stylistic/space-in-parens"], info:{...deprecated object}}]`, `Object.isFrozen` true.

## Get live surrounding code

**Retrieve:**

```ts
await mcp.codebase_memory.search_graph({ project: "eslint", query: "processLintReport usedDeprecatedRulesCache getDeprecatedRuleReplacements", limit: 10, fields: ["signature", "name", "file"] });
// Expected anchors: lib/eslint/eslint.js :115-209 (direct-read confirmed at pin)
```

## Verdict

Adopt lazy getter attachment over eager computation (cheap results, pay-per-inspection), the Config-keyed WeakMap memo, and the frozen-array contract. Adapt the descriptor to your host's property semantics. Omit the new-format `info` passthrough if your host has no structured deprecation metadata. Critical porting note: whatever your cache serialization does, it must strip or never see this property — the upstream test pins its absence across repeated cached runs.
