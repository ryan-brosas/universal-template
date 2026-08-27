<!-- capsule-v2 -->
# workspace-file-index-ttl-worker — how do you serve fast whole-workspace file listings to many consumers without blocking exit or re-walking per call?

**Source:** Cline Apache-2.0 `main@4f836ae7d0ed29ece7ef4a2a478deb470fdd056e`; Codebase Memory `cline`. **Question:** What shape lets one module be simultaneously a TTL cache, a single-flight builder, and its own worker thread — degrading safely everywhere?

## TTL cache + pending join + self-hosted unref'd worker with null-on-timeout same-thread fallback
**Path/Symbol:** `sdk/packages/core/src/services/workspace/file-indexer.ts` (`getFileIndex` :315-357; `pruneStaleCacheEntries` :65-77; `FileIndexWorkerClient` :204-282; `buildIndexInBackground` :298-313; `walkDir` :120-154; `prewarmFileIndex` :359-364).
**Signature:** `getFileIndex(cwd, {ttlMs?}?): Promise<Set<string>>` (POSIX-relative paths); `prewarmFileIndex(cwd, options?)` = forced rebuild via `ttlMs: 0`.
**Data Shape:** Module-level `CACHE: Map<cwd, {files:Set, lastBuiltAt, lastAccessedAt, pending}>`. Constants: TTL 15_000ms default; stale eviction after 10min of lastAccessedAt; worker request timeout 1_000ms; 10 excluded dirs (.git, node_modules, dist, build, .next, coverage, .turbo, .cache, target, out).

### Decisive source
```ts
function pruneStaleCacheEntries(now: number): void {
	if (CACHE.size <= 1) { return; }              // a lone workspace's cache is IMMORTAL until TTL rebuild
	for (const [cwd, entry] of CACHE.entries()) {
		if (entry.pending) continue;               // never evict under an in-flight build
		if (now - entry.lastAccessedAt > STALE_CACHE_EVICTION_MS) CACHE.delete(cwd);
	}
}
// Worker duality: THIS module is the worker entry — new Worker(new URL(import.meta.url))
// runs startWorkerServer() at import when !isMainThread; client worker.unref()'d so it
// never blocks process exit. requestIndex timeout RESOLVES NULL (not reject):
setTimeout(() => { this.pending.delete(requestId); resolve(null); }, WORKER_INDEX_REQUEST_TIMEOUT_MS).unref();
// buildIndexInBackground: null | thrown | worker-error ⇒ same-thread buildIndex(cwd).
// Walk ladder: rg --files --hidden -g !.git (windowsHide) → fallback recursive readdir;
// EACCES/EPERM/ENOENT are skip-not-fail per readdir AND per subtree recursion.
```

**Flow:** caller → prune → TTL hit (ttlMs>0 ∧ fresh ∧ files.size>0) returns cached Set → else join existing `pending` (single-flight; interim entry keeps OLD files+lastBuiltAt so concurrent callers see stale-but-real data) → else start `buildIndexInBackground`, store interim entry, return the promise which overwrites the entry on resolution.
**Invariant:** Consumers always get either fresh data or the newest known-good set — never an empty set during rebuilds; worker failure/timeout/slowness degrades to in-thread walking instead of failing the request; the module's own import-time worker-server branch makes client and worker share one source file.
**Probe:** `grep -cF 'if (CACHE.size <= 1) {' sdk/packages/core/src/services/workspace/file-indexer.ts` → 1 (:66). Test pins (`file-indexer.test.ts`, 5 cases read whole): "always excludes .git files from index", "prewarm rebuilds index and includes new files", "skips unreadable directories during fallback indexing", "evicts stale workspace indexes after 10 minutes when multiple workspaces exist" (:117, fake timers).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.get_code_snippet({ project: "cline", qualified_name: "cline.sdk.packages.core.src.services.workspace.file-indexer.getFileIndex" });
// observed: Function lines 315-357 verbatim; trace_path inbound callers_total=16
// (CLI autocomplete/welcome/App/runAgent/main, desktop sidecar ×3, vscode file-read
// executor, builtin-tools/executors/search chain, LocalRuntimeHost ×2, prewarm,
// mention-enricher)
```

## Verdict
Adopt TTL+single-flight caching with interim-stale entries, size-guarded eviction, self-hosted unref'd workers, and null-on-timeout same-thread fallback for opportunistic indexing. Adapt exclude lists and rg availability handling. Coverage caveats recorded honestly: both test suites mock worker_threads (`isMainThread:false`) so tests exercise the SAME-THREAD path; `file-indexer.test.ts:9` parse_partial flag is the type-only `vi.importActual<...>` mock argument, read directly. Runner-BLOCKED honestly (no node_modules).
