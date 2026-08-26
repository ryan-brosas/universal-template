<!-- capsule-v2 -->
# Semver range matcher echo protocol - how does a helper process answer batched version-compatibility questions?

**Source:** PhpStorm Light installed build PS-262.9421 (proprietary; cite-only); Codebase Memory `jetbrains-phpstorm-light`. **Question:** What is the minimal request/response contract for asking "does installed X satisfy required range R?" from a spawned Node helper — including the edge cases that make naive `satisfies()` wrong?

## javascript-plugin helpers/package-version-range-matcher/semver-range-matcher.js
**Path/Symbol:** `plugins/javascript-plugin/helpers/package-version-range-matcher/semver-range-matcher.js:match` (:3-23, sole export). Direct test shipped upstream: `test/version-range-test.js` (:1-57, mocha describe/it over a local expect() wrapper).
**Signature:** `match(requests) → responses`; request `{packageName, versionRange, version}` → response echoes all three + `validVersion`, `validVersionRange` (booleans), `matched`.
**Data Shape:** batch-in/batch-out array echo; tri-state honesty: `matched` is ABSENT (undefined), not false, when either input is invalid.

### Decisive source
```js
response.validVersion     = !!semver.valid(request.version);
response.validVersionRange = !!semver.validRange(request.versionRange);
if (response.validVersion && response.validVersionRange) {
  if (request.versionRange === '*') response.matched = true;   // short-circuit WITHOUT satisfies()
  else response.matched = semver.satisfies(request.version, request.versionRange);
}
// no else: invalid inputs ⇒ matched stays undefined
```
Upstream test pins the two traps: `'*', '4.0.0-beta.3' ⇒ matched true` (plain `satisfies(v,'*')` is FALSE for prereleases without includePrerelease — hence the short-circuit); `'latest' | 'file:../dyl' | 'git://...' ⇒ validVersionRange false, matched undefined`.

**Flow:** The parent batches all package questions into one spawn; the matcher answers per item with an echoed envelope so responses can be correlated without ids. The `'*'` fast path exists because prerelease versions must count as compatible with any-range — semver.satisfies would exclude them by default. Invalid ranges like git URLs or `latest` are classified via `validRange` instead of crashing satisfies.
**Invariant:** echo-identical request fields in every response; validity reported independently of matchability; `undefined` ≠ `false` (absent field distinguishes "unanswerable" from "answered-no"); `'*'` never consults satisfies.
**Probe:** mocha runner ABSENT from the install → executed the shipped test TABLE through the matcher's own entry (node v26.7.0): 13/13 rows reproduced GREEN incl. `*` vs `4.0.0-beta.3` ⇒ true, `latest`/git-URL ⇒ matched undefined + validVersionRange false, `~1.2.3` split (1.2.4 true / 1.3.4 false), echo fields strict-equal.
**Coverage caveat:** coverage no_recorded_issue ×3 (matcher, test, node-core-loader sibling path) @ gen 2026-08-24T13:57:05Z.

## Get live surrounding code
```ts
await mcp.codebase_memory.get_code_snippet({ project: "jetbrains-phpstorm-light", qualified_name: "jetbrains-phpstorm-light.plugins.javascript-plugin.helpers.package-version-range-matcher.semver-range-matcher.match" });
```

## Verdict
Adopt the echo-envelope batch protocol for any small decision helper process. ALWAYS add the any-range/prerelease short-circuit if you use semver.satisfies for compatibility gating. Keep unanswerable distinct from negative via undefined. Omit batching only for interactive single queries.
