<!-- capsule-v2 -->
# Honest incremental fact cache — how does a JSONL content-hash cache stay fast AND refuse to persist broken extraction?

**Source:** pi-fovea MIT `DETACHED@217a103`; Codebase Memory `pi-fovea`. **Question:** Extraction is a pure function of file content, but ast-grep invocations fail (bad binary, maxBuffer) — how do you get green-node reuse across sessions while guaranteeing one bad invocation can't poison warm starts?

## Streaming v9 cache + stat manifest + taint ledger
**Path/Symbol:** `src/core/build.ts:loadFacts/refreshFacts/extractInto/settleTaint/clearTaint/persistFacts/loadDiskStore/makeTextBudget` (:46-742); ledger source `src/core/astgrep.ts:recordFailure/drainExtractionFailures` (:95-104).
**Signature:** `loadFacts(root, files): Promise<{store, report: {failed,unreadable,oversized}, dirty}>`; `refreshFacts(root, store, files, changed, deletedPaths)` — callers pass optimistic hint sets; "an under-inclusive one is merely stale until the next full sweep".
**Data Shape:** Cache = `$TMPDIR/pi-fovea-<sha1(root)[:16]>.json`, `CACHE_VERSION=9`, header line `{fovea,root,rulesSha}` + one fact line per file with stat manifest `{size,mtime}`. Failed files persist ONLY `{file,sha1,size,mtime,failed:true}` — no partial semantic facts cross the cache boundary.

### Decisive source
```ts
// Honesty rule: facts implicated in a FAILED ast-grep pass are tainted. They
// serve the live session (a thin graph beats none) but are never persisted,
// so one bad invocation can't poison warm starts forever.
if (store.failedSha.has(rel) && metaEquals(meta, cachedMeta)) {
  store.meta.set(rel, meta);
  continue; // unchanged known failure: report it, do not retry it
}
// Additive-only contract: a fact pass drains the global ledger twice (stage
// pass, then the anchor re-pass). Clearing batch taint belongs ONCE, BEFORE
// re-extraction starts; a mid-pass clear would wipe earlier drains.
clearTaint(store, dirty);
await extractInto(root, store, dirty, contents, {...});
settleTaint(store, new Set(files));
await applyRulePack(root, store, files, dirty);   // may re-anchor clean files too
settleTaint(store, new Set(files));               // second drain captures anchor-stage failures
```
```ts
// Hash passes touch every dirty file; holding every text until extraction
// ends pins ALL source in memory (one such probe OOM-killed the host).
const TEXT_RETAIN_TOTAL = 16*1024*1024, TEXT_RETAIN_FILE = 128*1024;
// Records are replaced IMMUTABLY per refresh: a baseline snapshot holding the
// previous object must keep seeing the previous generation.
store.facts.set(f, { sha1: prev?.sha1 ?? "", symbols: [], ... });
```

**Flow:** load disk store (streamed line-wise, torn line = that file re-extracts; version/root mismatch = cold start) → prune vanished files → stat manifest sweep (unchanged stats skip read+hash entirely) → hash only the rest within a bounded text budget (16 MiB / 128 KiB per file; overflow lazily re-read via FileSource) → clear taint once → extract in 64-file batches → drain failure ledger into taint twice → applyRulePack re-anchors exactly what tier-3 promotion leaves stale (full set when rulesSha changed, dirty batch otherwise) → atomic tmp+rename persist (debounced 1.5s on refreshes), cache failures never fail the build.
**Invariant:** A failed extraction keeps its fact-free hash marker visible across launches WITHOUT retrying unchanged broken extraction every start (`report.failed` still lists it); content identical under moved mtime reuses facts; oversized (>1 MiB default) files keep their place in the model's view via the report, never silently vanish; graph version = sha1 of sorted `file:sha1` pairs.
**Probe:** `tests/report.test.ts` — fake ast-grep wrapper ("answers --version but exits 1 for everything else" — stderr distinguishes real failures from grep-convention exit-1-on-zero-matches): "names the implicated files when every ast-grep invocation fails"; unchanged-failure non-retry assertion; "reports zero failures and drains a previous run's ledger"; umbrella walk treats nested `.git` files/dirs as project boundaries and skips `.cargo` caches.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pi-fovea", query: "loadFacts refreshFacts tainted failedSha", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt: streaming JSONL cache with header-version invalidation, stat-manifest fast path, bounded hash-time prefetch, immutable per-generation records, the taint ledger drained exactly twice per pass, and honest coverage reporting (thin graph ≠ small repo). Adapt batch size/budgets to scale. Omit the v8 single-document compatibility note (historical).
