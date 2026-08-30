<!-- capsule-v2 -->
# Ignored-result taxonomy & warnIgnored override — why exactly was this file skipped, and who decides whether to say so?

**Source:** ESLint MIT `main@c27bc926e496985eb7911c09eb60914b2e4b5d0f` (tag v10.9.0); Codebase Memory project `eslint` (direct source+test fallback — graph not connected this session). **Question:** A porter must reproduce the four ignore reasons verbatim and the per-call override of the constructor's `warnIgnored`.

## createIgnoreResult four-way taxonomy

**Path/Symbol:** `lib/eslint/eslint-helpers.js:createIgnoreResult` (:674-722); consumed at `lintFile` (:1236-1241) and `lintText` (:1173-1181); `lintText` warnIgnored resolution (:1164-1170).
**Signature:** `createIgnoreResult(filePath: string, baseDir: string, configStatus: "ignored" | "external" | "unconfigured"): LintResult`.
**Data Shape:** Returns a single-warning result: `severity 1, ruleId null, fatal false, suppressedMessages [], errorCount 0, warningCount 1, fatalErrorCount 0, fixableErrorCount 0, fixableWarningCount 0`.

### Decisive source

```js
		case "external":
			message = "File ignored because outside of base path.";
			break;
		case "unconfigured":
			message =
				"File ignored because no matching configuration was supplied.";
			break;
		default:
			{
				const isInNodeModules =
					baseDir &&
					path
						.dirname(path.relative(baseDir, filePath))
						.split(path.sep)
						.includes("node_modules");

				if (isInNodeModules) {
					message =
						'File ignored by default because it is located under the node_modules directory. Use ignore pattern "!**/node_modules/" to disable file ignore settings or use "--no-warn-ignored" to suppress this warning.';
				} else {
					message =
						'File ignored because of a matching ignore pattern. Use "--no-ignore" to disable file ignore settings or use "--no-warn-ignored" to suppress this warning.';
				}
			}
```

```js
			const shouldWarnIgnored =
				typeof warnIgnored === "boolean"
					? warnIgnored
					: constructorWarnIgnored;
```

**Flow:** Four reasons, keyed by `configStatus`: `external` (outside base path), `unconfigured` (no matching configuration), and the default split where `dirname(relative(baseDir, filePath)).split(sep).includes("node_modules")` separates the DEFAULT node_modules ignore (hint: `"!**/node_modules/"` pattern) from an explicit ignore-pattern match (hint: `--no-ignore`). All four messages embed their own remediation flags. In `lintText`, the per-call `warnIgnored` boolean OVERRIDES the constructor value in BOTH directions (call-true over ctor-false warns; call-false over ctor-true — and absence falls back to the constructor value); an ignored file with warnings suppressed yields NO result (`results.length === 0`). Suppressions are applied in `lintText` only when `filePath` was given (`!filePath || !applySuppressions` gate) — anonymous `"<text>"` runs never reach the suppressions service.
**Invariant:** the four message strings are API surface (tests pin them byte-exact); the node_modules split must use the RELATIVE path's dirname, not the absolute path; the per-call override must be a full replacement (boolean wins over constructor), not a merge.
**Probe:** `tests/lib/eslint/eslint.js` ignore-taxonomy suites (:715-905 — unconfigured/external/pattern/node_modules messages; :843-871 the ctor-false/call-true override; :876-905 both suppression directions; :1209-1228 node_modules default despite `--no-ignore`). Executed: `npx mocha tests/lib/eslint/eslint.js --grep "warnIgnored"` → 9 passing. Executed live probe: all four messages byte-observed via `lintText` with `warnIgnored:true`; override probed both directions (`ctor-false call-true → 1 result severity 1`; `ctor-false no-call-opt → 0 results`).

## Get live surrounding code

**Retrieve:**

```ts
await mcp.codebase_memory.search_graph({ project: "eslint", query: "createIgnoreResult configStatus warnIgnored node_modules ignored", limit: 10, fields: ["signature", "name", "file"] });
// Expected anchors: lib/eslint/eslint-helpers.js :674-722; lib/eslint/eslint.js :1164-1181 (direct-read confirmed at pin)
```

## Verdict

Adopt the four-way taxonomy with remediation hints embedded in the message, and the per-call-overrides-constructor precedence. Adapt the node_modules detection to your host's path semantics (the relative-dirname trick is what makes `--no-ignore` still skip node_modules). Omit nothing behavioral. Coverage caveat: the `"ignored"` configStatus arm (explicit ignore during file discovery) is exercised through the lintFiles path; the lintText probes here cover external/unconfigured/node_modules/pattern directly.
