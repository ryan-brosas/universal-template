<!-- capsule-v2 -->
# Lint result cache — when is a cached lint result valid, and what must be stripped before persisting?

**Source:** ESLint MIT `main@dc1e7a8416937edefe04cf836ee202a6fc03bedd`; Codebase Memory project `eslint`. **Question:** How do you skip unchanged files without ever reusing a stale result after config changes?

## LintResultCache validity contract
**Path/Symbol:** `lib/cli-engine/lint-result-cache.js:LintResultCache` (:72–218).
**Signature:** `getCachedLintResults(filePath, config)`, `getValidCachedLintResults(filePath, config)`, `setCachedLintResults(filePath, config, result)`, `reconcile()`.
**Data Shape:** wraps `file-entry-cache`; per-entry meta stores `{ results, hashOfConfig }`; strategy `"metadata"` (mtime/size) or `"content"` (checksum); config hash = `hash(pkg.version + "_" + nodeVersion + "_" + stableStringify(config))`, WeakMap-cached per Config object.

### Decisive source
```js
// getValidCachedLintResults — cached results are valid iff ALL of:
// 1. the file is present, 2. it has not changed, 3. the config hash matches
const changed = fileDescriptor.changed || fileDescriptor.meta.hashOfConfig !== hashOfConfig;
if (changed) return null;
return fileDescriptor.meta.results;

// setCachedLintResults — two guards:
if (result && Object.hasOwn(result, "output")) return;      // never cache fixed output
if (Object.hasOwn(resultToSerialize, "source")) {
  resultToSerialize.source = null;                          // null sentinel: reread on next hit
}
```

**Flow:** lookup → invalid if file missing / descriptor.changed / config-hash mismatch → on hit, shallow-clone and rehydrate `source:null` by reading the file from disk → store strips unserializable fields and refuses entries whose `output` exists (fixes may not have been written to disk yet).
**Invariant:** the config hash binds cached results to the *exact* effective config (plus ESLint+Node version), so any config edit invalidates globally per-file; caching results containing an `output` field would resurrect fixes that were never persisted — hence the hard skip. The `source:null` sentinel keeps the cache small while making hits indistinguishable from fresh reads.
**Probe:** `tests/lib/cli-engine/lint-result-cache.js` (validity trio, output-skip, source rehydration).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "eslint", query: "LintResultCache getCachedLintResults hashOfConfig reconcile", limit: 10, fields: ["signature", "name", "file"] });
await mcp.codebase_memory.get_code_snippet({ project: "eslint", qualified_name: "eslint.lib.cli-engine.lint-result-cache.LintResultCache" });
```

## Verdict
Adopt the three-condition validity check, versioned config hashing with WeakMap cache, the no-fixed-output guard, and the null-source rehydration sentinel; adapt the storage backend (file-entry-cache → host store) and strategy names; omit the CLI flag plumbing around it.
