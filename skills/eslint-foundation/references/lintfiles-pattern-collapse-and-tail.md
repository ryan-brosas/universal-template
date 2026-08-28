<!-- capsule-v2 -->
# lintFiles pattern collapse & tail ordering — what does `lintFiles` do with degenerate patterns, and in what order do cache persistence, suppression, and report decoration run?

**Source:** ESLint MIT `main@c27bc926e496985eb7911c09eb60914b2e4b5d0f` (tag v10.9.0); Codebase Memory project `eslint` (graph NOT connected at authoring time — direct source+test reading fallback per AGENTS.md). **Question:** A porter must reproduce the exact pre-flight normalization of `patterns` and the load-bearing order of the run tail.

## lintFiles pre-flight & five-stage tail

**Path/Symbol:** `lib/eslint/eslint.js:ESLint.lintFiles` (:961-1094).
**Signature:** `async lintFiles(patterns: string | string[]): Promise<LintResult[]>`.
**Data Shape:** `patterns` may be a non-empty string (wrapped to `[pattern]`), an array of non-empty strings, `""`, or `[]`. Everything else — space-only string, `[""]`, `["",""]`, `undefined` — throws. Reads `cacheFilePath`, `lintResultCache`, `options`, `warningService`, `suppressionsService` from the `privateMembers` WeakMap bundle.

### Decisive source

```js
		if (
			patterns === "" ||
			(Array.isArray(patterns) && patterns.length === 0)
		) {
			/*
			 * Special case: If `passOnNoPatterns` is true, then we just exit
			 * without doing any work.
			 */
			if (eslintOptions.passOnNoPatterns) {
				return [];
			}

			normalizedPatterns = ["."];
		} else {
			if (
				!isNonEmptyString(patterns) &&
				!isArrayOfNonEmptyString(patterns)
			) {
				throw new Error(
					"'patterns' must be a non-empty string or an array of non-empty strings",
				);
			}
```

**Flow:** (1) pre-flight: `""`/`[]` collapse to `["."]` UNLESS `passOnNoPatterns` returns `[]` without touching disk; single string wraps to `[pattern]`; non-conforming input throws the exact message above. (2) stale-cache hygiene: caching disabled + `cacheFilePath` present ⇒ `fs.unlink` it; the unlink error is rethrown ONLY if the file still exists afterwards (vanished mid-delete is swallowed). (3) `findFiles` → worker partition consulted THROUGH `module.exports.calculateWorkerCount` precisely so tests/tools can stub it (comment at :1043); `workerCount` truthy ⇒ multithreaded path with the poor-concurrency notice closure, else `lintFilesWithoutMultithreading`. (4) multithreaded results may contain `null` holes from failed workers — `results.filter(result => !!result)` runs BEFORE the tail. (5) tail order is load-bearing: `lintResultCache.reconcile()` persists the cache FIRST, then `suppressionsService.applySuppressions(unsuppressedResults, await suppressionsService.load())` when `applySuppressions` is on, then `processLintReport(this, results)` LAST so the lazy `usedDeprecatedRules` getter attaches to final results only.
**Invariant:** `passOnNoPatterns` must short-circuit before any disk/config work; cache reconcile must precede suppression application (suppressed-but-cached results stay recoverable); `processLintReport` must see the FINAL result array (post-filter, post-suppression) or the lazy getter binds to the wrong set.
**Probe:** `tests/lib/eslint/eslint.js` "Invalid inputs" (:2360-2377 — space-only string, `[""]`, `["",""]`, `undefined` all throw) and "Normalized inputs" (:2379-2420 — `""`/`[]` lint the cwd; `passOnNoPatterns: true` returns `[]`). Executed: `npx mocha tests/lib/eslint/eslint.js --grep "passOnNoPatterns|Fix Types|getErrorResults|outputFixes"` → 20 passing. Executed live probe: `lintFiles(undefined)` and `lintFiles(["",""])` both throw the exact message; `passOnNoPatterns` instance `lintFiles([])` → `[]`.

## Get live surrounding code

**Retrieve:**

```ts
await mcp.codebase_memory.search_graph({ project: "eslint", query: "lintFiles patterns passOnNoPatterns reconcile applySuppressions", limit: 10, fields: ["signature", "name", "file"] });
// Expected anchors: ESLint.lintFiles lib/eslint/eslint.js :961-1094 (direct-read confirmed at pin)
```

## Verdict

Adopt the collapse-to-cwd default with an explicit pass-through flag, the swallow-vanished-unlink guard, and the reconcile → suppress → decorate tail order. Adapt the worker-partition stub seam to your host's DI mechanism. Omit the multithreading notice text (host-specific copy). Coverage caveat: the cache-unlink swallow branch is source-confirmed only — no dedicated upstream test pins the vanished-mid-delete case.
