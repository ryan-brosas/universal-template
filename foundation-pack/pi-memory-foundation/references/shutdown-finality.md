<!-- capsule-v2 -->
# Shutdown finality — the last write runs inline while everything else stays debounced

**Source:** pi-memory (MIT) `main@39e6b998a2279c8fad4a2c6c64e26828c1d6023e`; Codebase Memory `pi-memory`. **Question:** When a debounced background indexer is about to lose its process, how do you guarantee the final writes are indexed without making every write pay an inline cost?

## Shutdown finality
**Path/Symbol:** `index.ts:runQmdUpdateNow` (:1182–1190); debounced twin `scheduleQmdUpdate` (:1172–1180, 500 ms debounce → `execFileFn("qmd", ["update"], { timeout: 30_000 }, () => ensureQmdEmbed())`); inline call at shutdown (:1519); timer cleanup in `finally` (:1524–1526).
**Signature:** `async function runQmdUpdateNow(): Promise<void>`; `scheduleQmdUpdate(): void`.
**Data Shape:** module state `updateTimer: ReturnType<typeof setTimeout> | null` (read via `_getUpdateTimer`, cleared via `_clearUpdateTimer`). Mode gate from `PI_MEMORY_QMD_UPDATE ∈ {background (default), off}`.

### Decisive source
```ts
// runQmdUpdateNow (1182-1190): same mode gate as the debounce, then AWAIT the update
if (getQmdUpdateMode() !== "background") return;
if (!qmdAvailable) return;
await new Promise<void>((resolve) => {
  execFileFn("qmd", ["update"], { timeout: 30_000 }, () => resolve());
});
// Embeds for the final writes are picked up by the session_start catch-up
// embed; not chained here so shutdown stays fast.
```

**Flow:** every write tool calls the cheap path — `ensureQmdAvailableForUpdate()` (lazy re-detect only in background mode) + 500 ms-debounced `scheduleQmdUpdate()`. On a real exit (`session_shutdown` with a persisted summary), the hook instead awaits `runQmdUpdateNow()` inline so the index catches up before the process dies. The comment pins the boundary: embeddings are NOT chained here — the next session's catch-up embed covers them. In all paths the pending debounce timer is cleared in `finally`.

**Invariant:** one code path per timing class — debounce for throughput during the session, exactly one awaited update for durability at the end; both share the same mode gate (`off` never spawns qmd), and a cancelled timer never fires after shutdown.

**Probe:** `test/unit.test.ts` — `session_shutdown clears update timer` (:1403): `_getUpdateTimer()` non-null after `scheduleQmdUpdate()`, null after `hooks.session_shutdown({}, createShutdownCtx())`; `session_shutdown is safe when no timer exists` (:1411). Coverage caveat: `runQmdUpdateNow`'s awaited spawn itself has no dedicated upstream test (mode-gate behavior shared with `scheduleQmdUpdate`/`ensureQmdEmbed`, which are tested via `_setExecFileForTest` stubs).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-memory", query: "runQmdUpdateNow scheduleQmdUpdate _getUpdateTimer _clearUpdateTimer", limit: 6, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the two-path split: debounced updates for steady-state writes, one inline awaited flush on terminal events, with timer cleanup in `finally`. Adapt the 500 ms debounce and 30 s child timeout to your indexer's latency budget. Omit nothing — the "don't chain embeds at shutdown; catch up next start" decision is the porting lesson.
