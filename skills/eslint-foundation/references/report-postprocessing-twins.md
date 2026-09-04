<!-- capsule-v2 -->
# Report post-processing static twins — how do `outputFixes` and `getErrorResults` treat their inputs, and what do they silently drop?

**Source:** ESLint MIT `main@c27bc926e496985eb7911c09eb60914b2e4b5d0f` (tag v10.9.0); Codebase Memory project `eslint` (direct source+test fallback — graph not connected this session). **Question:** A porter must reproduce the write-side filter/throw behavior and the error-only projection without mutating caller-owned results.

## ESLint.outputFixes / ESLint.getErrorResults

**Path/Symbol:** `lib/eslint/eslint.js:ESLint.outputFixes` (:804-828), `ESLint.getErrorResults` (:835-857), shared `isErrorMessage` helper (eslint-helpers.js :662-665).
**Signature:** `static async outputFixes(results: LintResult[]): Promise<void>`; `static getErrorResults(results: LintResult[]): LintResult[]`.
**Data Shape:** `outputFixes` writes `result.output` to `result.filePath` via `fs.writeFile` under a per-call `Retrier(fileRetryCodes, {concurrency: 100})`. `getErrorResults` returns a NEW array of spread-copied results.

### Decisive source

```js
		await Promise.all(
			results
				.filter(result => {
					if (typeof result !== "object" || result === null) {
						throw new Error("'results' must include only objects");
					}
					return (
						typeof result.output === "string" &&
						path.isAbsolute(result.filePath)
					);
				})
				.map(r =>
					retrier.retry(() => fs.writeFile(r.filePath, r.output)),
				),
		);
```

```js
			if (filteredMessages.length > 0) {
				filtered.push({
					...result,
					messages: filteredMessages,
					suppressedMessages: filteredSuppressedMessages,
					errorCount: filteredMessages.length,
					warningCount: 0,
					fixableErrorCount: result.fixableErrorCount,
					fixableWarningCount: 0,
				});
			}
```

**Flow:** `outputFixes` — array guard first (`"'results' must be an array"`), then the filter VALIDATES while selecting: a non-object element throws MID-FILTER (`"'results' must include only objects"`), results without string `output` or with relative `filePath` are silently SKIPPED (not errors), survivors write concurrently under their own per-call Retrier (ENFILE/EMFILE, concurrency 100). `fs.writeFile` CREATES missing targets. `getErrorResults` — filters `severity === 2` from BOTH `messages` and `suppressedMessages`, spread-copies (inputs never mutated), recounts `errorCount`, zeroes `warningCount`/`fixableWarningCount`, PRESERVES `fixableErrorCount` as-is (it is not recomputed from the filtered messages), carries `fatalErrorCount` by spread, and DROPS files with zero errors entirely (the push is inside the `filteredMessages.length > 0` branch).
**Invariant:** neither twin may mutate its input; `outputFixes` must throw on non-object elements even when they would not have been selected by the output/abs-path predicate (validation precedes selection inside the same filter pass); `getErrorResults` must keep `fixableErrorCount` untouched even though some fixable errors may have been warnings-adjacent — the count describes the ORIGINAL error set.
**Probe:** `tests/lib/eslint/eslint.js` `describe("getErrorResults()")` (:10262-10400, incl. "should not mutate passed report parameter" :10297) and `describe("outputFixes()")` (:11321-11408, sinon-spied `fs.writeFile` exact-arg assertions + non-object throw). Executed: within the 20-passing mocha subset. Executed live probe: `outputFixes` created a missing tmp target with the given content; a relative-path entry was silently skipped; `[null]` threw `'results' must include only objects`; `getErrorResults` left the input array length unchanged, filtered 2→1 messages, `warningCount 0`, `fixableErrorCount` preserved.

## Get live surrounding code

**Retrieve:**

```ts
await mcp.codebase_memory.search_graph({ project: "eslint", query: "outputFixes getErrorResults isErrorMessage writeFile retrier", limit: 10, fields: ["signature", "name", "file"] });
// Expected anchors: lib/eslint/eslint.js :804-857 (direct-read confirmed at pin)
```

## Verdict

Adopt the validate-while-filtering pattern (throw on structural garbage, silently skip semantically inapplicable entries) and the non-mutating spread projection. Adapt the retry wrapper to your host's fs layer. Omit the per-call Retrier only if your host serializes writes elsewhere. Porting trap: recomputing `fixableErrorCount` from filtered messages would BREAK the upstream-pinned preserved count — copy it through.
