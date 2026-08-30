<!-- capsule-v2 -->
# ESLint options error accumulation — which removed eslintrc-era options get migration hints, and does one bad option fail the whole constructor?

**Source:** ESLint MIT `main@c27bc926e496985eb7911c09eb60914b2e4b5d0f` (tag v10.9.0); Codebase Memory project `eslint` (direct source+test fallback — graph not connected this session). **Question:** A porter must reproduce the fail-all validation surface: every problem reported in ONE error, with exact migration hints for removed keys.

## processOptions fail-all validation

**Path/Symbol:** `lib/eslint/eslint-helpers.js:processOptions` (:768-960), `ESLintInvalidOptionsError` (same file), consumed at `lib/eslint/eslint.js:717` (constructor).
**Signature:** `processOptions(options: object): ESLintOptions` — throws `ESLintInvalidOptionsError` whose message joins ALL accumulated errors with newlines.
**Data Shape:** Destructures ~24 known options with defaults (`allowInlineConfig:true, baseConfig:null, cache:false, cacheLocation:".eslintcache", cacheStrategy:"metadata", concurrency:"off", cwd:process.cwd(), errorOnUnmatchedPattern:true, fix:false, fixTypes:null, flags:[], globInputPaths:true, ignore:true, ignorePatterns:null, overrideConfig:null, overrideConfigFile:null, plugins:{}, stats:false, warnIgnored:true, passOnNoPatterns:false, ruleFilter:() => true, applySuppressions:false, suppressionsLocation:DEFAULT_SUPPRESSIONS_FILENAME`); the rest lands in `unknownOptions`.

### Decisive source

```js
	if (unknownOptionKeys.length >= 1) {
		errors.push(`Unknown options: ${unknownOptionKeys.join(", ")}`);
		if (unknownOptionKeys.includes("cacheFile")) {
			errors.push(
				"'cacheFile' has been removed. Please use the 'cacheLocation' option instead.",
			);
		}
		if (unknownOptionKeys.includes("configFile")) {
			errors.push(
				"'configFile' has been removed. Please use the 'overrideConfigFile' option instead.",
			);
		}
		// ... envs, extensions, resolvePluginsRelativeTo, globals,
		// ignorePath, ignorePattern, parser, parserOptions, rules,
		// rulePaths, reportUnusedDisableDirectives follow the same pattern
```

```js
	if (Array.isArray(plugins)) {
		errors.push(
			"'plugins' doesn't add plugins to configuration to load. Please use the 'overrideConfig.plugins' option instead.",
		);
	}
```

**Flow:** ALL validation runs before any throw: unknown keys first produce a summary line plus, for each of the EXACT 13 removed eslintrc-era keys (cacheFile, configFile, envs, extensions, resolvePluginsRelativeTo, globals, ignorePath, ignorePattern, parser, parserOptions, rules, rulePaths, reportUnusedDisableDirectives), a targeted migration hint pointing at its flat-config replacement (most under `overrideConfig.*`, `cacheFile`→`cacheLocation`, `rulePaths`→"define your rules using plugins"). Then per-option type checks append their own errors (booleans, absolute cwd, concurrency tri-state, fixTypes enum, overrideConfigFile tri-state string/null/true, plugins object-not-array + no-empty-string-key). Only after every check does `errors.length > 0` throw ONE `ESLintInvalidOptionsError` containing everything — an unknown key AND an unrelated type error appear in the SAME message.
**Invariant:** validation must be fail-all (never fail-fast) so users see every problem in one round-trip; the 13 hints must name the exact replacement option; the plugins-array case gets its own explanatory error because passing an array there is a category mistake, not a type error.
**Probe:** `tests/lib/eslint/eslint.js` removed-options + wrong-type fail-all assertions (:253-332 — one message containing the unknown-list, migration hints, AND an unrelated type error). Executed live probe (pass-9 era, re-confirmed by direct read at this pin): `processOptions` with an unknown list + migration hints + an unrelated type error in ONE thrown message; `overrideConfigFile:true` survives validation (tri-state) while `overrideConfigFile:42` does not.

## Get live surrounding code

**Retrieve:**

```ts
await mcp.codebase_memory.search_graph({ project: "eslint", query: "processOptions ESLintInvalidOptionsError removed options migration", limit: 10, fields: ["signature", "name", "file"] });
// Expected anchors: lib/eslint/eslint-helpers.js :768-960 (direct-read confirmed at pin)
```

## Verdict

Adopt fail-all option validation with a single aggregated error and targeted migration hints for renamed/removed keys. Adapt the hint text to your host's option names. Omit nothing behavioral — the fail-all property is the porting point: fail-fast validation here would force users through N constructor round-trips. Note this capsule re-delivers the pass-8 orphan file (which claimed 12 hints); the source enumerates exactly 13 — that count defect is repaired here.
