<!-- capsule-v2 -->
# Redis-sync document lock claim — how does a cluster route every edit for one doc to exactly one server?

**Source:** docmost AGPL-3.0 `main@549cf7c0053bb4f4c3c4e08d588b1f0c69297daf`; Codebase Memory `ext-docmost`. **Question:** How do N collab servers agree which single instance owns a document's Yjs merge authority, without a coordination service?

## Redis lock claim (`SET PX NX GET`) + throttled promise cache
**Path/Symbol:** `apps/server/src/collaboration/extensions/redis-sync/redis-sync.extension.ts`:`getOrClaimLock` / `getOrClaimLockThrottled` / `maintainLock` (lines 153–180, 237–246).
**Signature:** `getOrClaimLock(documentName: string): Promise<ServerId | null>`; `maintainLock(documentName: string): Promise<void>`.
**Data Shape:** Redis key `<prefix>Lock:<documentName>` holds the owning `serverId` (`collab-<hostname>-<nanoid(10)>`). Defaults: `lockTTL = 10_000ms`, prefix `'collab'`. Returns the *previous* owner's id when the claim loses the NX race.

### Decisive source
```ts
private getOrClaimLock(documentName: string) {
  const lockPromise = this.pub.set(
    this.getKey(documentName),
    this.serverId,
    'PX',
    this.lockTTL,
    'NX',
    'GET',
  );
  this.lockPromises[documentName] = lockPromise;
  // Briefly cache the serverId that claimed the doc to reduce load on redis
  // When the claimant unloads the doc, it will send an unload message to immediately clear this
  // a lockTTL / 2 guarantees stale reads < lockTTL upon server crash
  setTimeout(() => {
    delete this.lockPromises[documentName];
  }, this.lockTTL / 2);
  return lockPromise;
}

async maintainLock(documentName: string) {
  this.locks[documentName] = setInterval(() => {
    this.pub.set(this.getKey(documentName), this.serverId, 'PX', this.lockTTL);
  }, this.lockTTL / 2);
}
```

**Flow:** message arrives → `getOrClaimLockThrottled` returns cached claim promise if fresh → else atomic `SET key id PX ttl NX GET` → winner loads the doc and starts `maintainLock` heartbeat (re-SET without NX every `lockTTL/2`) → loser reads winner's serverId and proxies → owner unload publishes `{type:'unload'}` so peers drop their cached claim instantly; crash path relies on TTL expiry ≤ `lockTTL`.
**Invariant:** at most one live owner per document; stale-owner visibility after a crash is bounded by `lockTTL`, never by the local cache (cache TTL is half the lock TTL). The heartbeat interval must stay < lockTTL or ownership silently expires mid-session.
**Probe:** `grep -cF "'GET'," apps/server/src/collaboration/extensions/redis-sync/redis-sync.extension.ts` (=1; the GET option that makes the losing claim return the current owner) and `grep -cF 'lockTTL / 2' apps/server/src/collaboration/extensions/redis-sync/redis-sync.extension.ts` (=3: cache clear, comment, heartbeat interval).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-docmost", query: "RedisSyncExtension getOrClaimLock maintainLock lock", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the single-key `SET PX NX GET` claim + half-TTL heartbeat as the portable multi-instance routing primitive; adapt the transport (any shared KV with atomic compare-and-set works); omit docmost's NestJS/ioredis wiring and msgpackr packing. No direct unit test exists upstream for this class — behavior pinned here by source inspection plus deterministic probes.
