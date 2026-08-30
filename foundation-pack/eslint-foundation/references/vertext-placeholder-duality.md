<!-- capsule-v2 -->
# verifyText `<text>`⇄placeholder duality — how does stdin-style text resolve a real config while the result still reports `"<text>"`?

**Source:** ESLint MIT `main@c27bc926e496985eb7911c09eb60914b2e4b5d0f` (tag v10.9.0); Codebase Memory project `eslint` (direct source+test fallback — graph not connected this session). **Question:** A porter must reproduce the swap that lets anonymous text participate in config resolution, and the conditional attachment of `output`/`source`.

## verifyText placeholder swap & result-shaping

**Path/Symbol:** `lib/eslint/eslint-helpers.js:verifyText` (:1133-1202), `getPlaceholderPath` (:648-650).
**Signature:** `verifyText({ text, cwd, filePath, configs, fix, allowInlineConfig, ruleFilter, stats, linter }): LintResult`.
**Data Shape:** `filePath` may be `"<text>"` (lintText anonymous) or an absolute path (lintFile). `getPlaceholderPath(cwd) = path.join(cwd, "__placeholder__.js")`. Returns a LintResult with conditional `output`/`source`/`stats` keys.

### Decisive source

```js
	const filePathToVerify =
		filePath === "<text>" ? getPlaceholderPath(cwd) : filePath;
	const { fixed, messages, output } = linter.verifyAndFix(text, configs, {
		allowInlineConfig,
		filename: filePathToVerify,
		fix,
		ruleFilter,
		stats,

		filterCodeBlock(blockFilename) {
			return configs.getConfig(blockFilename) !== void 0;
		},
	});
```

```js
	if (fixed) {
		result.output = output;
	}

	if (
		result.errorCount + result.warningCount > 0 &&
		typeof result.output === "undefined"
	) {
		result.source = text;
	}
```

**Flow:** The linter receives the placeholder path so flat-config resolution finds a REAL config for the text (the linter itself has no cwd); the RESULT keeps `filePath: "<text>"` (or `path.resolve(filePath)` for real files), so callers never see the placeholder. `filterCodeBlock` adopts a processor block only if `configs.getConfig` resolves it — this OVERRIDES the linter's default `blockFilename.endsWith(".js")` gate (linter.js :909-911), making block adoption config-driven at the orchestration layer. `output` is attached iff `fixed`; `source` is attached iff there are problems AND no output (unfixed problems keep the original text for reporters; a fatal parse error therefore reports `filePath:"<text>"` with `source` present). `stats` attaches `{times: linter.getTimes(), fixPasses: linter.getFixPassCount()}`.
**Invariant:** the placeholder path must never leak into a result's `filePath`; `source` and `output` must never both be present (output implies fixed implies the original text is stale); block adoption must consult the config array, not the file extension, when a config array is available.
**Probe:** `tests/lib/eslint/eslint.js` `"<text>"` deepStrictEqual suite (:1172-1206 — fatal parse error result shape with `source` string). Executed: within the 11-passing mocha subset. Executed live probe: fatal-parse `lintText` → `filePath:"<text>"`, `source` typeof string, `messages[0].fatal === true`.

## Get live surrounding code

**Retrieve:**

```ts
await mcp.codebase_memory.search_graph({ project: "eslint", query: "verifyText getPlaceholderPath filterCodeBlock __placeholder__", limit: 10, fields: ["signature", "name", "file"] });
// Expected anchors: lib/eslint/eslint-helpers.js :1133-1202 / :648-650 (direct-read confirmed at pin)
```

## Verdict

Adopt the swap-in/swap-out duality: resolve config under a synthetic real path, report under the public name. Adapt the placeholder filename to your host's convention (keep it deterministic per cwd). Omit the legacy `.endsWith(".js")` default only if your host guarantees a config array at every call site. Boundary note: the linter-side default filter and the `__placeholder__.js` linter-level default are owned by the verify-pipeline / processor-routing capsules; this capsule owns strictly the orchestration-layer swap, adoption override, and conditional attachment.
