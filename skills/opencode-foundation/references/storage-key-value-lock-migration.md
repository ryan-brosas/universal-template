<!-- capsule-v2 -->
# Storage key/value lock + migration ladder — how do you build a crash-tolerant JSON key/value store with safe concurrent updates and one-shot schema migrations?

**Source:** opencode MIT `dev@03521003fafd`; Codebase Memory `opencode`. **Question:** Legacy opencode persists sessions/messages/diffs as JSON files under a global data dir. How does the store keep concurrent read-modify-write cycles lossless without a database, map filesystem absence to a typed error the HTTP layer can turn into 404s, and run schema migrations exactly once per version even when a step fails?

## Per-target reentrant locks + dual-shape ENOENT
**Path/Symbol:** `packages/opencode/src/storage/storage.ts` (`missing` :67-74, `parseMigration` :76-78, `MIGRATIONS` :81-211, layer state/locks :213-244, `fail`/`wrap` :245-250, `withResolved` :255-264, `remove` :266-270, `read` :272-278, `update` :280-294, `write` :296-300, `list` :301-313).
**Signature:** `read<T>(key: string[]) → Effect<T, FSUtil.Error | NotFoundError>`; `update<T>(key, fn: (draft: T) => void) → Effect<T, ...>`; `write<T>(key, content) → Effect<void, FSUtil.Error>`; `remove(key) → Effect<void, FSUtil.Error>`; `list(prefix) → Effect<string[][], FSUtil.Error>`; key = string[] path segments, file = `path.join(dir, ...key) + ".json"`.
**Data Shape:** `NotFoundError{message: "Resource not found: <target>"}` (tagged `_tag:"NotFoundError"`) — the exact shape `mapStorageNotFound` in session-http-handler-plane.md converts to API 404. Locks: `RcMap<string, TxReentrantLock>` keyed by resolved file path, `idleTimeToLive: 0`.

### Decisive source
```ts
// storage.ts:67-74 — missing() recognizes BOTH ENOENT shapes so either FS impl works:
function missing(err: unknown) {
  if (!err || typeof err !== "object") return false
  if ("code" in err && err.code === "ENOENT") return true
  if ("reason" in err && err.reason && typeof err.reason === "object" && "_tag" in err.reason) {
    return err.reason._tag === "NotFound"
  }
  return false
}
// storage.ts:280-294 — update is read-mutate-write under the WRITE lock for this target only:
const update = <T>(key: string[], fn: (draft: T) => void) =>
  Effect.gen(function* () {
    const value = yield* withResolved(key, (target, rw) =>
      TxReentrantLock.withWriteLock(rw, Effect.gen(function* () {
        const content = yield* wrap(target, fs.readJson(target))
        fn(content as T)
        yield* writeJson(target, content)
        return content
      })),
    )
    return value as T
  })
```

**Flow:** Every operation resolves its key to an absolute file path under `Global.Path.data/storage`, then takes that path's lock from the RcMap: `read` takes the READ lock (concurrent reads never block each other), `update`/`write`/`remove` take the WRITE lock (per-target, not global — different keys proceed in parallel). `read`/`update` wrap the raw FS call so a missing file becomes typed `NotFoundError` with the full target path in the message; `remove` treats missing as success; `list` globs `**/*` under the prefix dir, catches any failure to `[]`, strips the `.json` suffix (`slice(0,-5)`), and sorts by `join("/").localeCompare`. State (the data dir) is `Effect.cached` so it resolves once per process.
**Invariant:** A lost-update on one key is impossible while two fibers call `update` on it — the test pins 25 unbounded concurrent increments landing at exactly 25. Absence is always the same typed error regardless of which FS implementation produced it. Remove is idempotent; list of a missing prefix is `[]`, never an error.
**Probe:** `packages/opencode/test/storage/storage.test.ts` ("serializes concurrent updates for the same key" pins 25 unbounded updates → `{value: 25}`; "concurrent reads do not block each other" pins 10 parallel reads; "maps missing reads to NotFoundError" pins `_tag:"NotFoundError"` with the `.json` target path in the message; "remove on missing key is a no-op"; "list on missing prefix returns empty"); source pin:
```bash
grep -n 'err.reason._tag === "NotFound"' packages/opencode/src/storage/storage.ts
grep -n 'TxReentrantLock.withWriteLock' packages/opencode/src/storage/storage.ts
```
expect 1 + 3 hits (remove/update/write).

## Marker-file migration ladder
**Path/Symbol:** `packages/opencode/src/storage/storage.ts` (state gen :219-244, `MIGRATIONS` array :80-215, migration 1 legacy project→session/message/part re-layout + git root-hash project IDs, migration 2 summary.diffs → session_diff split).
**Signature:** marker file `<dir>/migration` holds a base-10 integer; `parseMigration` maps NaN → 0; missing marker → 0.
**Data Shape:** each migration is `(dir, fs, git) → Effect<void, FSUtil.Error>`; the ladder runs `MIGRATIONS[i]` for `i` in `marker..MIGRATIONS.length`.

### Decisive source
```ts
// storage.ts:225-240 — failure logs and breaks WITHOUT writing the marker:
const migration = yield* fs.readFileString(marker).pipe(
  Effect.map(parseMigration),
  Effect.catchIf(missing, () => Effect.succeed(0)),
  Effect.orElseSucceed(() => 0),
)
for (let i = migration; i < MIGRATIONS.length; i++) {
  yield* Effect.logInfo("running migration", { index: i })
  const exit = yield* Effect.exit(step(dir, fs, git))
  if (Exit.isFailure(exit)) {
    yield* Effect.logError("failed to run migration", { index: i, cause: exit.cause })
    break
  }
  yield* fs.writeWithDirs(marker, String(i + 1))
}
```

**Flow:** On first state resolution the ladder reads the marker (invalid content like "wat" parses to NaN → 0, so a corrupt marker re-runs from the start — migrations must be idempotent or tolerant), then executes each pending step capturing its Exit. A failed step is logged and BREAKS the loop without advancing the marker, so the next boot retries the same step; a successful step writes `i+1` immediately. Migration 1 re-lays out legacy per-project dirs into the global `project/session/message/part` tree, deriving project IDs from `git rev-list --max-parents=0` sorted first root hash, tolerating malformed legacy records (decode failures skip the record, not the batch). Migration 2 splits `summary.diffs` out of session files into `session_diff/<id>` and replaces the summary with aggregated additions/deletions.
**Invariant:** The marker never advances past a failed step — crash tolerance comes from retrying the same step, so every migration must tolerate already-migrated input. Marker content is trusted only as an integer; anything else means "start over".
**Probe:** `packages/opencode/test/storage/storage.test.ts` ("migration 2 runs when marker contents are invalid" stages marker "wat" + a legacy session file, pins session_diff created and summary replaced with `{additions: 5, deletions: 5}`, marker ends "2"; "migration 1 tolerates malformed legacy records" pins partial migration past a `"[]"` probe file; "failed migrations do not advance the marker" pins NO marker file existing after a step fails on a truncated JSON record); source pin:
```bash
grep -n 'Effect.catchIf(missing, () => Effect.succeed(0))' packages/opencode/src/storage/storage.ts
grep -n 'fs.writeWithDirs(marker, String(i + 1))' packages/opencode/src/storage/storage.ts
```
expect 1 + 1 hits.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "opencode", query: "Storage Service read update write list TxReentrantLock RcMap parseMigration MIGRATIONS", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt per-target (not global) reentrant locks keyed by resolved path for file-backed stores: readers parallel, writers exclusive per key, no cross-key contention. Adopt dual-shape absence detection when your store may run over multiple FS abstractions, and make the absence error carry the full target path so upper layers can build useful 404 messages. Adopt the marker-file migration ladder with fail-without-advance semantics — it buys crash tolerance for free if every step tolerates re-running. Adapt the JSON-suffix key encoding and localeCompare listing to your layout; omit the git-root-hash project-ID derivation unless you migrate pre-existing per-project directories. Direct test read whole (storage.test.ts); bun runner blocked at this checkout (no node_modules), probes are byte-exact greps.
