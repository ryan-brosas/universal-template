<!-- capsule-v2 -->
# Per-file lint lifecycle — how does one file move through config resolution, cache short-circuit, read, abort, and retry?

**Source:** ESLint MIT `main@c27bc926e496985eb7911c09eb60914b2e4b5d0f` (tag v10.9.0); Codebase Memory project `eslint` (direct source+test fallback — graph not connected this session). **Question:** A porter must reproduce the per-file gate ladder: when is a file skipped, when is the cache trusted, and how do abort and retry interact?

## lintFile gate / cache-mirror / read-retry / abort plane

**Path/Symbol:** `lib/eslint/eslint-helpers.js:lintFile` (:1216-1320).
**Signature:** `async lintFile(filePath, configs, eslintOptions, linter, lintResultCache, readFileCounter, retrier, controller): Promise<LintResult | undefined>`.
**Data Shape:** `configs` is the FlatConfigArray; `lintResultCache` may be `null`; `readFileCounter` is `{ duration: bigint }` or undefined; `retrier` retries on `fileRetryCodes = new Set(["ENFILE", "EMFILE"])` (eslint.js :96); `controller` is the run-shared AbortController.

### Decisive source

```js
	if (!config) {
		if (warnIgnored) {
			const configStatus = configs.getConfigStatus(filePath);

			return createIgnoreResult(filePath, cwd, configStatus);
		}

		return void 0;
	}

	// Skip if there is cached result.
	if (lintResultCache) {
		const cachedResult = lintResultCache.getCachedLintResults(
			filePath,
			config,
		);

		if (cachedResult) {
			const hadMessages =
				cachedResult.messages && cachedResult.messages.length > 0;

			if (hadMessages && fix) {
				debug(`Reprocessing cached file to allow autofix: ${filePath}`);
			} else {
				debug(`Skipping file since it hasn't changed: ${filePath}`);
				return cachedResult;
			}
		}
	}
```

**Flow:** (1) config gate: `configs.getConfig(filePath)` undefined ⇒ `warnIgnored ? createIgnoreResult(...) : undefined` — an ignored file without `warnIgnored` yields NO result object at all. (2) cache short-circuit EXCEPT `hadMessages && fix` ("Reprocessing cached file to allow autofix") — a cached file with messages is re-linted under fix mode so autofix can run in memory. (3) fixer built once per file via `getFixerForFixTypes`. (4) `readAndVerifyFile` reads with `{encoding:"utf8", signal: controller?.signal}`, times the read into `readFileCounter.duration`, then `controller?.signal.throwIfAborted()` AFTER the read — so one hard failure stops sibling files promptly. (5) `retrier.retry(readAndVerifyFile, { signal })` for ENFILE/EMFILE; the outer `.catch(error => { controller?.abort(error); throw error; })` aborts the SHARED controller then rethrows, so the first hard failure poisons the whole run.
**Invariant:** the abort check must come AFTER each read (not before) so an in-flight read is not silently discarded; a fix-mode run over a cached-with-messages file must NOT return the cached result (it would fix nothing); `warnIgnored:false` on an unconfigured file must produce `undefined`, not an empty result.
**Probe:** `tests/lib/eslint/eslint.js` cache suites (:13239+; "should not store `usedDeprecatedRules` in the cache file" :14287-14356 exercises the 3-run cached path) and the `calculateWorkerCount` suite (:12932-13052) pinning the surrounding partition. Executed: mocha subsets above (20 + 11 passing). Executed live probe: `warnIgnored:false` + ignored file via `lintText` returns `[]` (no result object); the reprocess-on-fix branch is source-confirmed and mirrors `needsReprocessing` in the cache plane (see result-cache capsule).
**Coverage caveat:** no dedicated upstream suite isolates the ENFILE/EMFILE retry ladder for `lintFile`; the retry codes table is read at eslint.js :96 and the Retrier is the external `@humanwhocodes/retry` package (lib/shared/retrier.js does not exist in-repo).

## Get live surrounding code

**Retrieve:**

```ts
await mcp.codebase_memory.search_graph({ project: "eslint", query: "lintFile getCachedLintResults throwIfAborted retrier ENFILE", limit: 10, fields: ["signature", "name", "file"] });
// Expected anchors: lib/eslint/eslint-helpers.js :1216-1320 (direct-read confirmed at pin)
```

## Verdict

Adopt the gate ladder order (config → cache → read → abort-check → retry) and the shared-controller abort-on-first-failure semantics. Adapt the retry code set to your host's filesystem. Omit the `readFileCounter` timing plumbing if your host has no net-linting-ratio reporting. Note the mirror contract: this function's "reprocess cached file with messages under fix" is the per-file twin of the cache plane's `needsReprocessing` planning predicate.
