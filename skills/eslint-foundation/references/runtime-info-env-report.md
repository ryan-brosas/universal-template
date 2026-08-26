<!-- capsule-v2 -->
# Runtime environment report — how does `--env-info` collect versions without repeating work, and what happens when a probe command fails?

**Source:** ESLint MIT `main@c27bc926e496985eb7911c09eb60914b2e4b5d0f` (tag v10.9.0); Codebase Memory project `eslint`. **Question:** How do I reproduce the diagnostic banner and its failure behavior?

## Closure-cached command probes with fail-hard rethrow

**Path/Symbol:** `lib/shared/runtime-info.js:environment` (:26-159) wrapping `execCommand` (:46-63), `getBinVersion` (:80-91), `getNpmPackageVersion` (:100-148), `isChildOfDirectory` (:35-37); `version` (:165-167); `module.exports = { environment, version }` (:173+).
**Signature:** `environment(): string` — joined 7-line banner; `version(): string` — package.json version.
**Data Shape:** Per-invocation `Map` keyed by the JOINED command string (`[cmd, ...args].join(" ")`) caches trimmed stdout; spawn failures throw the cross-spawn `process.error` after `log.error` decoration.

### Decisive source

```js
	function execCommand(cmd, args) {
		const key = [cmd, ...args].join(" ");

		if (cache.has(key)) {
			return cache.get(key);
		}

		const process = spawn.sync(cmd, args, { encoding: "utf8" });

		if (process.error) {
			throw process.error;
		}

		const result = process.stdout.trim();

		cache.set(key, result);
		return result;
	}
```

**Flow:** Banner = Node version, npm `--version`, LOCAL eslint (`npm ls --depth=0 --json eslint`), GLOBAL eslint (same plus `-g`), OS platform/release. Global check returning empty JSON — or JSON without `dependencies.eslint` — yields the literal string `"Not found"`. Otherwise `npm bin -g` output vs `process.argv[1]` decides `(Currently used)` via `!path.relative(parent, child).startsWith("..")`. Version strings normalize to a leading `v`.
**Invariant:** environment() is FAIL-HARD, not fail-soft: any subcommand failure logs `Error finding <pkg> version running the command ...` and RETHROWS — callers wrap `--env-info` in try/catch. The closure cache lives only for THIS call, so repeated banners re-execute probes (no cross-call poisoning). The npm ls JSON path hardcodes `dependencies.eslint` regardless of the `pkg` parameter.
**Probe:** No dedicated upstream suite exists for this module (recorded caveat). Executed behavioral probe from the repo root: `environment()` logged the decorated error and threw `TypeError: The "to" argument must be of type string. Received undefined` (cross-spawn surfaced npm's failure on this host) — confirming fail-hard rethrow; `version()` returned `v10.9.0`. Graph retrieval: qn_pattern over `eslint.lib.shared.runtime-info.*` enumerated all seven defs with line ranges (executed).

## Get live surrounding code

**Retrieve:**

```ts
await tools["mcp__codebase-memory__get_code_snippet"]({ project: "eslint", qualified_name: "eslint.lib.shared.runtime-info.environment" });
// → live source at :26-159 (executed)
```

## Verdict

Adopt per-invocation command caching keyed by the joined argv string, the Not-found/currently-used ladder, and fail-hard-with-decorated-log semantics. Adapt the probe commands to your package manager. Omit the hardcoded `dependencies.eslint` lookup only if you parameterize it — upstream did not.