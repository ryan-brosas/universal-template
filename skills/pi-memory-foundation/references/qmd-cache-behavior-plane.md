<!-- capsule-v2 -->
# qmd-cache behavior plane — how do you prove TTL caching, negative seeding, and setup-seeds-cache without real processes or timers?

**Source:** pi-memory (MIT, `main@39e6b998a2279c8fad4a2c6c64e26828c1d6023e`); Codebase Memory `pi-memory`. **Question:** How can a test suite prove that availability/collection checks are cached within their TTL, that a known-missing backend can be seeded into the cache, and that an install flow seeds the cache so follow-up checks are free — all deterministically?

## qmd-cache behavior plane
**Path/Symbol:** `test/qmd-cache.ts` — `mockExecFile` (:18–27); `detectQmd` TTL proof (:30–39); `checkCollection` TTL proof (:41–50); `_setQmdAvailable(false)` seeding (:52–53); `setupQmdCollection` seeds collection cache (:55–82); transitions env polarity (:84–100); `finally` reset (:103–105). Source under test: `index.ts:detectQmd` (:1074–1090), `checkCollection` (:1092–1126), collection-cache seed (:1069–1071).
**Signature:** `mockExecFile(handler: (cmd, args) => { error?: Error; stdout?: string }): () => number`; `detectQmd(): Promise<boolean>`; `checkCollection(name: string): Promise<boolean>`.
**Data Shape:** the fake replaces `execFileFn` via `_setExecFileForTest(fn)` and returns a zero-arg call counter; handlers assert exact `cmd`/`args` (`["collection","list"]` for detect, `["collection","list","--json"]` for collection lookup) and return `{}` or `{ stdout }`. Callbacks fire on `queueMicrotask`, preserving async semantics so awaited caches actually populate.

### Decisive source
```ts
// mockExecFile (18-27): counting fake that keeps the callback asynchronous
let calls = 0;
const fn: ExecFileFn = ((cmd, args, _options, callback) => {
	calls++;
	const result = handler(cmd, args);
	queueMicrotask(() => callback(result.error ?? null, result.stdout ?? "", ""));
}) as ExecFileFn;
_setExecFileForTest(fn);
return () => calls;

// index.ts detectQmd (1074-1090): TTL read happens BEFORE any process spawn
if (qmdAvailabilityCheckedAt && now - qmdAvailabilityCheckedAt < qmdStatusTtl(qmdAvailable)) {
	return Promise.resolve(qmdAvailable);
}
// probe uses `qmd collection list` (NOT `qmd status`) because `status` can
// trigger slow model/device probing and produce false negatives.

// index.ts setupQmdCollection tail (1069-1071): success writes the cache directly
qmdCollectionStatusCache.set("pi-memory", { checkedAt: Date.now(), exists: true });
```

**Flow:** (1) `_clearQmdStatusCaches()` resets module cache state; `mockExecFile` swaps in the fake. (2) Two consecutive `await detectQmd()` calls assert `true` twice while the counter stays at 1 — the second answer came from the positive-TTL cache. (3) Same shape proves `checkCollection("pi-memory")` caches its `--json` lookup. (4) `_setQmdAvailable(false)` seeds the availability cache WITHOUT executing anything; the next `detectQmd()` resolves `false` from that seed. (5) A hand-rolled fake distinguishes `collection add` / `context add` / `collection list`: after `setupQmdCollection()` succeeds once, a subsequent `checkCollection("pi-memory")` performs **zero** list calls because setup wrote the cache entry itself. (6) The same script pins `shouldSkipExitSummaryForReason` env polarity (default skips `reload`/`new`; `PI_MEMORY_SUMMARIZE_TRANSITIONS=1` includes them) with save/delete/restore of the env var. (7) `finally` runs `_resetExecFileForTest()` + `_clearQmdStatusCaches()` so no fake leaks across files.

**Invariant:** within the TTL window a repeated logical check must never re-spawn the backend; any code path that learns a definitive status (probe OR setup) must write it into the cache; every test must restore the real exec seam and clear caches in `finally` to stay order-independent.

**Probe:** EXECUTED pass 4: `bun test/qmd-cache.ts` → stdout `qmd cache tests passed`, exit 0 (see verification.md). Coverage caveat: this file is NOT wired into CI (`ci.yml` runs only `npm test` = unit suite; e2e workflow is dispatch-only) — it is a standalone try/finally script meant to be run ad hoc.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-memory", query: "mockExecFile detectQmd checkCollection _clearQmdStatusCaches", limit: 10, fields: ["signature", "name", "file"] });
```
Pass-4 retrieval: `search_graph` name_pattern `^(execute|flushCurrent|mark|shortSessionId|readFileSafe)$` + file_pattern `*qmd-cache*` located the plane; `get_code_snippet(pi-memory.test.qmd-cache.mockExecFile)` returned the excerpt above; `check_index_coverage(test/qmd-cache.ts)` = `no_recorded_issue`.

## Verdict
Adopt the counting-fake-exec pattern with microtask callbacks, the call-counter TTL proof (N awaits → 1 spawn), explicit negative-status seeding, and the setup-writes-cache assertion; adopt the save/delete/restore env protocol and the `finally` double reset. Adapt handler arg-shapes and cache keys to the host's backend. Omit the qmd-specific CLI arguments. Caveat: keep running this script manually or wire it into CI when porting — nothing else executes it.
