<!-- capsule-v2 -->
# models.dev catalog cache — how do you cache a remote model catalog across processes with atomic writes, TTL freshness, snapshot fallback, and a never-fail refresh?

**Source:** opencode MIT `dev@03521003fafd`; Codebase Memory `opencode`. **Question:** A coding-agent host needs the upstream model catalog (providers, models, costs, limits) available at startup even offline, refreshed periodically without blocking, and shared safely between concurrent CLI processes. How do you structure the cache so reads never fail and refreshes never corrupt?

## Disk-first populate ladder + invalidated-infinite cache
**Path/Symbol:** `packages/core/src/models-dev.ts` (`filepath`/`ttl`/`lockKey` :160-166, `fresh` :168-173, `fetchApi` :175-182, `loadFromDisk` :184-196, `loadSnapshot` :198-200, `fetchAndWrite` :202-215, `populate` :217-231, `cachedInvalidateWithTTL` :233, `refresh` :237-254, 60-min fork :256-258).
**Signature:** `get() → Effect<Record<string, Provider>>` (never fails); `refresh(force? = false) → Effect<void>` (never fails).
**Data Shape:** `Provider = {id, name, env: string[], npm?, api?, models: Record<string, Model>}`; cache file `Global.Path.cache/models.json` (or `models-<hash(source)>.json` for a custom `OPENCODE_MODELS_URL`); compile-time fallback `OPENCODE_MODELS_DEV` injected at build time.

### Decisive source
```ts
// models-dev.ts:217-233 — disk → snapshot → fetch, then cache forever until refresh invalidates
const populate = Effect.gen(function* () {
  const fromDisk = yield* loadFromDisk
  if (fromDisk) return fromDisk
  const snapshot = yield* loadSnapshot
  if (snapshot) return snapshot
  if (Flag.OPENCODE_DISABLE_MODELS_FETCH) return {}
  const text = yield* Effect.scoped(Effect.gen(function* () {
    yield* Flock.effect(lockKey)          // cross-process single-flight
    return yield* fetchAndWrite()
  }))
  return JSON.parse(text)
}).pipe(Effect.withSpan("ModelsDev.populate"), Effect.orDie)
const [cachedGet, invalidate] = yield* Effect.cachedInvalidateWithTTL(populate, Duration.infinity)
```

**Flow:** `populate` tries the disk cache first (a corrupt file is deleted and treated as absent — `loadFromDisk` catches FileSystemError on readJson and removes the file); then the bundled snapshot; then a fetch under a cross-process `Flock.effect` lock, written atomically (`writeWithDirs` to a `pid+timestamp .tmp` file → `rename`, removing the tempfile on failure). The result is memoized with an infinite TTL — `get()` never touches disk again until `refresh()` calls `invalidate`. `refresh(force=false)` checks the 5-minute mtime freshness BEFORE and AGAIN UNDER the lock (double-checked: another process may have refreshed between check and lock), fetches, writes, invalidates, and publishes `Event.Refreshed`; the whole body is `Effect.ignore`d after logging — a failed refresh leaves the old cache serving. HTTP fetches carry `retryTransient` (2 tries, jittered exponential from 200ms) and a 10s timeout with a channel/version User-Agent. At layer construction a fiber repeats `refresh()` every 60 minutes (`Schedule.spaced` — runs once, then waits between completions).
**Invariant:** `get()` is total — every failure path (no disk, no snapshot, fetch disabled, corrupt file) yields a usable value (`{}` at worst); cache writes are atomic so a crash never leaves a truncated file; concurrent processes serialize on the flock and the under-lock freshness re-check prevents duplicate fetches; refresh failure degrades to stale data, never to an error.
**Probe:** `packages/core/test/models.test.ts` (290L, 9 `it.live`): "get() returns providers from disk when cache file exists" pins zero HTTP calls on a fresh cache; "get() recovers from a corrupted cache file by fetching a fresh catalog" pins delete-then-refetch; "refresh(false) skips fetch when on-disk file is fresh" / "fetches when stale" pin the mtime TTL; "refresh swallows HTTP errors and leaves cache intact" pins the never-fail refresh (500 status → old fixture still served). Source pin:
```bash
grep -c 'cachedInvalidateWithTTL' packages/core/src/models-dev.ts # expect 1
grep -c 'Flock.effect' packages/core/src/models-dev.ts           # expect 2
grep -c 'it.live' packages/core/test/models.test.ts              # expect 9
grep -c 'Layer.fresh' packages/core/test/models.test.ts          # expect 2
```

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "opencode", query: "ModelsDev populate disk snapshot fetch Flock cachedInvalidateWithTTL refresh invalidate Event.Refreshed atomic rename", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the populate ladder (disk → bundled snapshot → locked fetch), atomic tempfile+rename writes, double-checked freshness under a cross-process lock, and the never-fail refresh that invalidates an infinite-TTL memo. Adapt the cache location, TTL (5min) and repeat interval (60min); omit the Effect HttpClient/Flock specifics if your host has equivalents. Coverage caveat: the custom-source `models-<hash>.json` filename branch is source-confirmed only (tests pin the default `models.json` path); Codebase Memory MCP not connected this session, Retrieve marked for re-execution on graph reconnect; bun runner blocked at this checkout, probes are byte-exact greps.
