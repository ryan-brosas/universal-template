<!-- capsule-v2 -->
# Lint result cache — when is a cached lint result valid, what may mutate it, and when does it hit disk?

**Source:** ESLint MIT `main@c27bc926e496985eb7911c09eb60914b2e4b5d0f`; Codebase Memory project `eslint`. **Question:** How do you skip unchanged files without ever reusing a stale result after config changes — and who is allowed to write the cache?

## LintResultCache validity + update-existing-only writes + single run-tail reconcile
**Path/Symbol:** `lib/cli-engine/lint-result-cache.js` (whole file, 220 lines): `configHashCache` module-level WeakMap (:38), `hashOfConfigFor` (:50–60), constructor strategy assert + `useChecksum` mapping (:78–100), `getCachedLintResults` shallow-clone + source rehydration (:109–133), `getValidCachedLintResults` (:143–172), `setCachedLintResults` (:183–211), `reconcile` pure delegation (:214–217). Call sites: `lib/eslint/eslint.js` reconcile at the lintFiles tail AFTER both thread modes and BEFORE applySuppressions (:1076–1079); main-side cache re-apply from returned worker results (:583–595); sequential twin set (:645–649); per-file read short-circuit in `lib/eslint/eslint-helpers.js:lintFile` (:1244–1258); worker-side own cache instance `lib/eslint/worker.js` :88–95.
**Signature:** `new LintResultCache(cacheFileLocation, "metadata" | "content")`; `getCachedLintResults(filePath, config)`, `getValidCachedLintResults(filePath, config)`, `setCachedLintResults(filePath, config, result)`, `reconcile()`.
**Data Shape:** wraps `file-entry-cache`; per-entry meta stores `{ results, hashOfConfig }`; strategy `"metadata"` (mtime/size) or `"content"` (checksum, `useChecksum = cacheStrategy === "content"`); config hash = `hash(pkg.version + "_" + nodeVersion + "_" + stableStringify(config))`, memoized per Config object in a MODULE-LEVEL WeakMap.

### Decisive source
```js
// getValidCachedLintResults — cached results are valid iff ALL of:
// 1. the file is present, 2. it has not changed, 3. the config hash matches
const fileDescriptor = this.fileEntryCache.getFileDescriptor(filePath);
if (fileDescriptor.notFound) return null;          // absence checked BEFORE change/hash
const changed = fileDescriptor.changed || fileDescriptor.meta.hashOfConfig !== hashOfConfig;
if (changed) return null;
return fileDescriptor.meta.results;

// setCachedLintResults — two guards, then UPDATE-EXISTING-ONLY:
if (result && Object.hasOwn(result, "output")) return;   // never cache fixed output
const fileDescriptor = this.fileEntryCache.getFileDescriptor(filePath);
if (fileDescriptor && !fileDescriptor.notFound) {        // never CREATES entries
    const resultToSerialize = Object.assign({}, result);
    if (Object.hasOwn(resultToSerialize, "source")) resultToSerialize.source = null;
    fileDescriptor.meta.results = resultToSerialize;
    fileDescriptor.meta.hashOfConfig = hashOfConfigFor(config);
}

// reconcile — pure delegation; its ONLY call site is the lintFiles run tail:
reconcile() { this.fileEntryCache.reconcile(); }
```

**Flow:** lookup → null if descriptor notFound (checked first) / descriptor.changed / config-hash mismatch → on hit, shallow-clone (`{...cachedResults}` so later mutation can't leak into the store) and rehydrate `source: null` by rereading the file from disk → store strips `source` to a null sentinel and refuses any result owning `output` (fixes may not have been written to disk yet) → the in-memory entry cache persists exactly ONCE per run: lintFiles calls `reconcile()` after both thread modes return and before applySuppressions. Multithreaded nuance: each worker builds its OWN LintResultCache over the same cache file (worker.js :88–95) so workers READ shared cached entries from disk, but their in-memory updates are never reconciled — main re-applies `setCachedLintResults` from the returned results (eslint.js :583–595) and persists once. Read-shared, write-via-main.
**Invariant:** the config hash binds cached results to the *exact* effective config (plus ESLint+Node version), so any config edit invalidates globally per-file; caching results containing an `output` field would resurrect fixes that were never persisted — hence the hard skip (fix-mode runs NEVER populate the cache). The `source:null` sentinel keeps the cache small while making hits indistinguishable from fresh reads. Writers are constrained to descriptors file-entry-cache already knows about (file exists on disk AND was touched via getFileDescriptor) — set-on-ghost-file is a no-op and a subsequent reconcile persists NOTHING (cache file not even written). The shallow clone on read means all intentional cache mutation flows through setCachedLintResults only (issue #13507 comment).
**Probe:** `tests/lib/cli-engine/lint-result-cache.js` (constructor asserts :87–118; validity trio :211–279 incl. not-found-first; output-skip "does not modify file entry" :316–327; notFound-descriptor "does not modify file entry" :329–344; source-excepted storage :346–403; reconcile delegation stub :405–433). Live probes this pass: set-on-ghost-file + reconcile → 0 entries, no cache file written; valid set → entry meta `{size, mtime, results, hashOfConfig}` with `source: null` persisted; set-with-output → output NOT persisted; hit rehydrated `source` byte-identical to disk contents; different-config lookup → null (hash mismatch); content-strategy after same-mtime edit → null (checksum changed). Mocha subset `tests/lib/cli-engine/lint-result-cache.js` → 17 passing.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "eslint", query: "LintResultCache getCachedLintResults hashOfConfigFor reconcile setCachedLintResults", limit: 10, fields: ["signature", "name", "file"] });
await mcp.codebase_memory.get_code_snippet({ project: "eslint", qualified_name: "eslint.lib.cli-engine.lint-result-cache.LintResultCache" });
```

## Verdict
Adopt the three-condition validity check (absence before change before hash), versioned config hashing with a WeakMap memo keyed by the config object, the no-fixed-output guard, the null-source rehydration sentinel, and the single run-tail persist with update-existing-only writes; in a worker pool, let workers read the shared cache but funnel all writes through the coordinator's instance. Adapt the storage backend (file-entry-cache → host store) and strategy names; omit the CLI flag plumbing around it. Caveat: Codebase Memory MCP was not connected in the mining session; anchors verified by direct byte-matched source reads at the git-clean pin.
