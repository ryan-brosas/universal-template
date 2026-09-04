<!-- capsule-v2 -->
# SQLite database node — how do you pick a per-channel DB file and initialize one global SQLite layer?

**Source:** opencode MIT `dev@03521003fafd`; Codebase Memory `opencode`. **Question:** how does one global database node choose its file per install channel, apply PRAGMAs + migrations at build time, and swap drivers between Bun and Node without changing consumers?

## Connected graph-selected seam
**Path/Symbol:** `packages/core/src/database/database.ts`: `Service` (:15-17), `layer` (:19-37), `layerFromPath` (:39-41), `path()` (:43-55), `node` (:57); `packages/core/src/database/sqlite.bun.ts`: `transactionAcquirer` (:110-117), `layer` (:175-181).
**Signature:** `path() => string`; `layerFromPath(filename: string) => Layer.Layer<Service>`; `node = makeGlobalNode({ service: Service, layer: layerFromPath(path()), deps: [] })`.
**Data Shape:** `Interface = { db: EffectDrizzleSqlite database }`; consumers destructure `Database.Service` for `{ db }`.

### Decisive source
```ts
yield* db.run("PRAGMA journal_mode = WAL")
yield* db.run("PRAGMA synchronous = NORMAL")
yield* db.run("PRAGMA busy_timeout = 5000")
yield* db.run("PRAGMA cache_size = -64000")
yield* db.run("PRAGMA foreign_keys = ON")
yield* db.run("PRAGMA wal_checkpoint(PASSIVE)")
yield* DatabaseMigration.apply(db)
...
}).pipe(Effect.orDie),
```
```ts
if (Flag.OPENCODE_DB) {
  if (Flag.OPENCODE_DB === ":memory:" || isAbsolute(Flag.OPENCODE_DB)) return Flag.OPENCODE_DB
  return join(Global.Path.data, Flag.OPENCODE_DB)
}
if (["latest", "beta", "prod"].includes(InstallationChannel) || process.env.OPENCODE_DISABLE_CHANNEL_DB === "1" ...)
  return join(Global.Path.data, "opencode.db")
return join(Global.Path.data, `opencode-${InstallationChannel.replace(/[^a-zA-Z0-9._-]/g, "-")}.db`)
```

**Flow:** `path()` resolves env override (":memory:"/absolute verbatim, relative joined onto the data dir) → channel-suffixed `opencode-<channel>.db` for non-{latest,beta,prod} channels with `[^a-zA-Z0-9._-]` sanitized to `-`, plain `opencode.db` otherwise → `layerFromPath` builds the layer: PRAGMA ladder + `DatabaseMigration.apply(db)`, all `Effect.orDie` (a DB that cannot initialize is a defect, not a recoverable error) → driver selection via the package-imports condition map `"#sqlite": {bun: sqlite.bun.ts, node: sqlite.node.ts, default: bun}`. Both drivers: single connection behind a semaphore-1 acquirer; `transactionAcquirer` takes the semaphore and releases it via a SCOPE FINALIZER, so a transaction holds the connection lock until its scope closes; `executeStream` dies (no streaming); safeIntegers read from the fiber context; errors classify into `SqlError`. The Bun driver adds `serialize()`/`loadExtension`; its native layer runs `PRAGMA journal_mode = WAL` unless `disableWAL`.
**Invariant:** exactly one global node with `deps: []` (nothing below it); initialization failure dies — callers never see a half-initialized DB; the transaction lock is scope-bound, not call-bound.
**Probe:** `packages/core/test/database-migration.test.ts` (:41-49 two concurrent `Database.layerFromPath(filename)` builds under `Effect.all` must both succeed — the semaphore-serialized init), plus every `Database.node` consumer test (projector, permission saved, credential) which build through the same layer.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "opencode", query: "Database layerFromPath PRAGMA makeGlobalNode sqlite transactionAcquirer", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the env-override → channel-suffix path ladder with character sanitization, the orDie initialization posture, and the scope-finalizer transaction lock. Adapt the PRAGMA values and the driver condition map to your runtime. Omit the Bun-only serialize/loadExtension surface unless you need DB snapshots. Coverage caveat: the node-side PRAGMA/migration sequence is exercised only through the migration test's layer builds (no dedicated database.test.ts); driver internals are source-confirmed.
