<!-- capsule-v2 -->
# Stats ingestion — lock, worker, apply, embedded dashboard

**Source:** Oh My Pi MIT `main@96f428097`; Codebase Memory `oh-my-pi`. **Path:** `packages/stats/src/aggregator.ts` + `sync-worker.ts` + `embedded-client.ts`. **Question:** How do you parallelize log parsing across workers while keeping every DB write on one contended-by-nobody handle — and ship a dashboard inside a compiled binary?

## Sync: one file lock, workers parse, main thread applies
**Path/Symbol:** `packages/stats/src/aggregator.ts:withStatsSyncLock` (63–72), `applyParseResult` (75), `syncAllSessions` (240–242) → `syncAllSessionsLocked` (244+), `smokeTestSyncWorker` (202–238).
**Signature:** `withStatsSyncLock<T>(dbPath, fn): Promise<T>` — native file lock `${dbPath}.sync`, retry 25 ms, total wait ≈1h; `syncAllSessions(opts?): Promise<{ processed, files }>`.
**Data Shape:** `SyncWorkerRequest = { kind?: "parse"; sessionFile; fromOffset } | { kind: "ping" }`; `SyncWorkerResponse = { ok:true; result } | { ok:true; kind:"pong" } | { ok:false; error }`; embedded archive = base64 of gzipped tar (gzip magic 0x1f 0x8b).

### Decisive source
```ts
// The lock covers file discovery, parsing, and the final SQLite write so a
// parse result for a session moved by GC can never commit after cleanup.
// The native lock is owned by an operating-system primitive, so an interrupted
// owner is released automatically and a live owner is never displaced.
export async function withStatsSyncLock<T>(dbPath: string, fn: () => Promise<T>): Promise<T> {
  await fs.promises.mkdir(path.dirname(dbPath), { recursive: true });
  return await withFileLock(`${dbPath}.sync`, fn, {
    retryDelayMs: STATS_SYNC_LOCK_RETRY_MS,
    retries: Math.ceil(STATS_SYNC_LOCK_WAIT_MS / STATS_SYNC_LOCK_RETRY_MS),
  });
}
```

**Flow:** (1) `withStatsSyncLock` wraps the whole sync so a parse result can never commit after GC moved a session; (2) main discovers session files + reads per-file offsets → parse only `fromOffset` onward; (3) tasks post 1:1 to workers via structured clone `{ sessionFile, fromOffset }` — worker runs `parseSessionFile` (pure IO+CPU, NO DB); larger pools run one in-flight job per worker while writes stay on the calling thread (`workers: 1` parses inline; darwin defaults to serial); (4) the single SQLite handle applies via `applyParseResult` — inserts stats/tool calls/links then `setFileOffset`. `onProgress` fires once per completed file including skips.

**Invariant:** the lock covers discovery→parse→write as ONE critical section; a live owner is never displaced and an interrupted owner auto-releases; only the main thread touches SQLite.

**Probe:** `smokeTestSyncWorker` ping `{kind:'ping'}` → `{ok:true,kind:'pong'}` with 5s timeout — exists because neither `--version` nor `stats --summary` exercises the spawn path on fresh installs (issues #1011 / #1027); no-op on darwin. Tests: `test/smoke-worker*.test.ts`, `test/acceptance*.test.ts`, `test/aggregator.test.ts`, `test/sync-worker.test.ts`.

## No DB in workers — structured-clone contracts
**Path/Symbol:** `sync-worker.ts` types.
**Invariant:** a failing parse never wedges the pool — the worker replies `{ok:false,error}` and the main thread records the skip and continues.

## Embedded dashboard: base64(gzip(tar)) with magic-bit rejection
**Path/Symbol:** `embedded-client.ts:decodeEmbeddedClientArchive` (19).

### Decisive source
```ts
const normalized = txt.replaceAll(/\s+/g, '');
if (!normalized) return null;
if (!/^[A-Za-z0-9+/]+={0,2}$/.test(normalized)) return null;
const bytes = Buffer.from(normalized, 'base64');
if (bytes[0] !== 0x1f || bytes[1] !== 0x8b) return null; // gzip magic
return bytes;
```

**Flow:** `embedded-client.generated.txt` holds base64 of gzipped tar of `dist/client`; populated by `gen:stats` for compiled binaries + prepacked bundles, reset empty afterwards so dev builds come from source. Decode rejects non-gzip blobs (0x1f 0x8b magic) INCLUDING the legacy `export const …` placeholder — that must be treated as *no archive*, never decoded garbage. Missing/degraded archive → dev build fallback, not a startup failure.

**Probe:** `test/embedded-client.test.ts` (base64/gzip round-trip, empty + placeholder cases). Coverage caveat: tests excluded from graph index by design.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "oh-my-pi", name_pattern: "^(withStatsSyncLock|syncAllSessions|applyParseResult|smokeTestSyncWorker|decodeEmbeddedClientArchive|parseSessionFile)$", limit: 14, fields: ["signature"] });
```

## Verdict
Adopt native-file-lock critical sections over discovery+parse+commit, parse-in-worker/write-on-main threading with structured-clone contracts, spawn smoke probes, and magic-byte-validated embedded assets; adapt lock paths, worker counts, and archive formats to host; omit the Bun/darwin-specific worker caveats unless targeting Bun.
