<!-- capsule-v2 -->
# Cohort cache-root separation — why is the cache directory fingerprint compared OUTSIDE the HELLO envelope?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** How do two builds with identical binaries but different cache roots avoid corrupting each other?

## Cache fingerprint in cohort lifetime, not stable HELLO
**Path/Symbol:** `src/daemon/service.h:29–35` (identity struct note) + `tests/test_version_cohort.c:232–267` (`version_cohort_rejects_exact_build_with_different_cache_root`, `version_cohort_rejects_missing_cache_fingerprint`).
**Signature:** field `const char *cache_fingerprint; /* SHA-256 of the canonical cache-root path */`
**Data Shape:** NULL ⇒ internal test/legacy identity with no cache namespace. The cohort lifetime layer REQUIRES matching cache fingerprints before any daemon/CLI work, while the wire HELLO envelope deliberately omits it so cross-build diagnosis stays possible.

### Decisive source
```c
/* SHA-256 of the canonical cache-root path. It is intentionally excluded
 * from the stable HELLO envelope, but the account-wide lifetime cohort
 * compares it before any daemon/CLI work can begin. NULL means an internal
 * test/legacy identity with no cache namespace. */
TEST(version_cohort_rejects_exact_build_with_different_cache_root) { ... }
```

**Flow:** compute sha256 of canonicalized cache root at startup → lifetime cohort admission compares it after build identity matches → mismatch ⇒ refuse (two cache domains must not share a daemon) → NULL tolerated only for tests/legacy.
**Invariant:** Wire compatibility and data-domain compatibility are DIFFERENT checks at DIFFERENT layers — merging them either breaks cross-version diagnosis or permits cache cross-talk.
**Probe:** the two named tests plus `version_cohort_rejects_same_hash_with_different_abi`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "cache_fingerprint", limit: 5 });
```

## Verdict
Adopt layered identity (wire vs domain) when builds may share endpoints but not state; adapt to your cache layout; the NULL-means-legacy escape hatch keeps old clients diagnosable.
