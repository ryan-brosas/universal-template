<!-- capsule-v2 -->
# DocSyncPeer job kernel — priority doc queue, five job types, clock-map dedup, permission-error taxonomy

**Source:** AFFiNE MIT `canary@b530198a3b5ec1fb9b9eb9b684e428ab9e387d5a` (packages/common/nbstore is unmarked but distributed in-repo; EE carve-out covers packages/backend + packages/common/native only); Codebase Memory project `ext-affine`. **Question:** How does the production client sync MANY docs against one remote with per-doc retry isolation and no redundant transfers?

## DocSyncPeer
**Path/Symbol:** `packages/common/nbstore/src/sync/doc/peer.ts`: `DocSyncPeer` (:152-908) — jobs map (:262-492), `retryLoop` (:628-846), `schedule` (:871-889), `docDiffUpdate` (:129-150).
**Signature:** job types `connect | push | pull | pullAndPush | save`; `addPriority(id, priority) → disposer`; `mainLoop(signal?)`.
**Data Shape:** `Status { docs, connectedDocs, docErrors: Map<docId,msg>, jobDocQueue: AsyncPriorityQueue<string>, jobMap: Map<docId, Job[]>, remoteClocks: ClockMap, syncing, retrying, skipped }`; sync metadata persists three clocks PER PEER+DOC: pushed / pulledRemote / remote.

### Decisive source
```ts
// connect decision — local-newer-or-unpushed ⇒ pullAndPush; else pull only if remote advanced
const pushedClock = (await this.syncMetadata.getPeerPushedClock(this.peerId, docId))?.timestamp ?? null;
const clock = await this.local.getDocTimestamp(docId);
if (!this.remote.isReadonly && clock && (pushedClock === null || pushedClock < clock.timestamp))
  await this.jobs.pullAndPush(docId, signal);
else {
  const pulled = (await this.syncMetadata.getPeerPulledRemoteClock(this.peerId, docId))?.timestamp ?? null;
  const remoteClock = this.status.remoteClocks.get(docId);
  if (remoteClock && (pulled === null || pulled < remoteClock)) await this.jobs.pull(docId, signal);
}
```
```ts
// strict per-doc execution ORDER inside the drain loop (:776-836)
const connect    = remove(jobs, j => j.type === 'connect');
const pullAndPush= remove(jobs, j => j.type === 'pullAndPush');
const pull       = remove(jobs, j => j.type === 'pull');
const push       = remove(jobs, j => j.type === 'push');   // batches ALL queued pushes into ONE merged update
const save       = remove(jobs, j => j.type === 'save');
```
```ts
// echo suppression is PREFIX-based so any peer instance with same peerId is recognized
private readonly uniqueId = `sync:${this.peerId}:${nanoid()}`;
if (origin === this.uniqueId || origin?.startsWith(`sync:${this.peerId}:`)) return;
```

**Flow:** mainLoop → retryLoop waits ≤30 s for all three storages to connect (timeout throws → retry), subscribes local+remote `subscribeDocUpdate`, seeds docs from BOTH local timestamps and remote clocks (`getDocTimestamps(maxClock)` delta fetch), then forever: pop highest-priority docId → drain its job list in fixed order → repeat. Errors: generic ⇒ whole-loop reset + 5 s backoff; `DOC_ACTION_DENIED|SPACE_ACCESS_DENIED` (name-matched) ⇒ record in docErrors, drop the doc's jobs, NEVER retried (runRemoteDocJob returns false).

**Invariant:** (1) Clock monotonicity is enforced by `ClockMap.setIfBigger` — a stale server event can never regress state or trigger re-pull. (2) Push coalescing merges every pending update for a doc into one binary BEFORE one remote write; skipping this multiplies server writes and races snapshot squashing. (3) Permission errors must be terminal PER DOC but non-fatal for the peer — treating them as generic errors loops forever on unreadable docs (upstream regression tests pin exactly this). (4) `pullAndPush` computes the reverse-diff via `docDiffUpdate(local, localSv, remoteDiff, remoteSv)` returning null when both sides already agree — porters who always push after pull create update storms between mirrors.

**Probe:** `packages/common/nbstore/src/__tests__/sync.spec.ts` :292-397 'doc' pins two-peer propagation through IndexedDB storages; :487-568 pins terminal-permission behavior (`expect(remote.pushCount).toBe(1)` after 1200 ms — no retry storm); `grep -c "setIfBigger" packages/common/nbstore/src/utils/clock.ts` == 1.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-affine", query: "DocSyncPeer schedule pullAndPush remoteClocks DOC_ACTION_DENIED", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the job taxonomy, fixed drain order, and three-clock metadata model; adapt transport and metadata store; omit the indexer-crawler plane (separate seam).
