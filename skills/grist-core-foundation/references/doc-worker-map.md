<!-- capsule-v2 -->
# DocWorkerMap — how do you assign documents to workers in Redis when every participant can die?

**Source:** grist-core MIT `main@b83224bbe9c88910dfeb28922df254a26f702f68`; Codebase Memory `grist-core`. **Question:** What is the correct lock/recheck/commit dance for doc→worker assignment, and how do elections, groups, and the in-process dummy differ?

## Redlock-guarded assignment with availability fallback and Dummy twin
**Path/Symbol:** `app/gen-server/lib/DocWorkerMap.ts:DocWorkerMap.assignDocWorker` (398–485), `getElection`/`removeElection` (546–576), `_getAvailableWorkerId(ByLoad)` (628–697), `DummyDocWorkerMap` (32–164), factory `getDocWorkerMap` (703–712); interface `app/server/lib/DocWorkerMap.ts:IDocWorkerMap` (41–82).
**Signature:** `assignDocWorker(docId: string, workerId?: string): Promise<DocStatus>`; `getElection(name, durationInMs): Promise<string | null>`.
**Data Shape:** redis keys — `workers`, `workers-available[-{group}]` sets; `workers-available-by-load-{group}` zset (score=load 0..1); `worker-{id}` hash + `-docs` set + `-group` str; `doc-${docId}` hash (JSON-string fields) + `-checksum` (24h TTL, literal `"null"` for null) + `-group`; lock key `workers-lock` (Redlock, 3s TTL); `elections-${deployment}` hash.

### Decisive source
```ts
// Fast path WITHOUT lock:
let docStatus = await this.getDocWorker(docId);
if (docStatus) { return docStatus; }
// Lock, then RECHECK — someone may have assigned while we waited:
const lock = await this._redlock.lock(`workers-lock`, LOCK_TIMEOUT);
try {
  const docAndChecksum = await this._getDocAndChecksum(docId);
  docStatus = docAndChecksum.doc;
  if (docStatus) { return docStatus; }
  const group = await this._client.getAsync(`doc-${docId}-group`) || DEFAULT_GROUP;
  workerId = await this._getAvailableWorkerId(group) || undefined;
  if (!workerId) {
    // No workers in desired group: fall back to ANY available worker rather than failing.
    log.warn(`... found no workers for group ${group}`);
    workerId = await this._client.srandmemberAsync("workers-available") || undefined;
  }
  if (!workerId) { throw new Error("no doc workers available"); }
  const result = await this._client.multi()
    .sadd(`worker-${workerId}-docs`, docId)
    .hmset(`doc-${docId}`, { docWorker: JSON.stringify(docWorker), isActive: JSON.stringify(true) })
    .setex(`doc-${docId}-checksum`, CHECKSUM_TTL_MSEC / 1000.0, checksum || "null")
    .execAsync();
} finally { await lock.unlock(); }
```

**Flow:** read assignment → hit ⇒ return immediately (no lock; assignments are HINTS that can be revoked anytime) → miss ⇒ redlock `workers-lock` → recheck under lock → pick worker from group set (random, or Lua weighted-random-by-complement-of-load behind `GRIST_EXPERIMENTAL_WORKER_ASSIGNMENT`) with cross-group fallback → write assignment atomically in a Multi (docs-set membership, status hash, checksum with TTL). `getElection` is a named TTL lease (`nomination-${name}`, uuid secret, SETEX under its own redlock) used so exactly one server runs housekeeping; removal verifies the secret and throws otherwise. The whole surface has an in-memory twin: `DummyDocWorkerMap` implements permits via `MapWithTTL`, elections via `MapWithCustomTTL(1ms default)`, and is served as a SINGLETON by `getDocWorkerMap()` when `REDIS_URL` is unset.
**Invariant:** assignment answers are advisory — clients must survive refusal/reassignment (worker death releases nothing gracefully); nulls are encoded as the STRING "null" because redis cannot store null; nested objects are JSON strings inside hashes; group exhaustion never fails an open (it degrades to any-worker with a warning, trading strict isolation for availability); election secrets are unguessable uuids and removal without the matching secret throws; the dummy keeps the same interface so single-process dev and tests need no redis.
**Probe:** no direct unit test for DocWorkerMap itself (coverage caveat: exercised through integration suites — `test/server/lib/Authorizer.ts`, `test/server/lib/HostedStorageManager.ts`, `test/server/lib/docTools.ts` use the dummy path; `test/server/lib/DocWorkerLoadTracker.ts` pins load reporting). Election semantics additionally consumed by `app/gen-server/lib/Housekeeper.ts`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "grist-core",
  query: "assignDocWorker getElection _getAvailableWorkerId", limit: 10,
  fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the read-fast-path / lock-recheck-commit ladder, the advisory-assignment contract, null/string encoding rules, and the interface-twin pattern (Redis impl + singleton in-memory dummy selected by env) for any shard-placement or work-assignment registry. Adapt the lock implementation (redlock → your store's CAS), group model, and load-weighting to host. Omit the deployment-scoped group-election machinery unless you run heterogeneous worker fleets.
