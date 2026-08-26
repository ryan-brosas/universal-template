<!-- capsule-v2 -->
# Per-platform cross-process lock — how do detached children, daemons, and orchestrators serialize access to one browser profile?

**Source:** LocoAgent MIT `main@c01bb3f8a7b06a0db9f697c5bea485947959d226`; Codebase Memory `locoagent`. **Question:** How do mutually distrusting OS processes (background `start`, long-lived `daemon`, parallel `orchestrate`) agree that a platform's single browser tab is busy — when state.json's read-modify-write is not atomic?

## Atomic create-exclusive file lock with pid + age staleness
**Path/Symbol:** `scripts/lib/platform-lock.ts`:`acquireLock`, `releaseLock`, `writeLock`, `isAlive`, `isStale` (`:53-115`; constants `:19-20`).
**Signature:** `acquireLock(platform: string, workflowId: string, root?: string): boolean`; `releaseLock(platform, workflowId, root?): void`.
**Data Shape:** Lock file `workflows/.locks/<platform>.lock` containing `{ pid, workflowId, acquiredAt: ISO }`. `STALE_LOCK_MS = 15 * 60 * 1000` (executors time out at 10 min; the extra 5 min absorbs clock skew before pid-reuse paranoia kicks in).

### Decisive source
```ts
const fd = openSync(path, 'wx') // atomic: fails with EEXIST if present
writeSync(fd, JSON.stringify({ pid: process.pid, workflowId, acquiredAt: new Date().toISOString() }))
closeSync(fd)
...
if (holder && isAlive(holder.pid) && !isStale(holder)) return false
// Stale: remove and recreate.
rmSync(path, { force: true })
return writeLock(path, workflowId)
```
with liveness via signal-0 probe:
```ts
try { process.kill(pid, 0); return true }
catch (e) { return e?.code === 'EPERM' }   // EPERM = exists but not ours → alive
```

**Flow:** try create-exclusive → on EEXIST inspect holder JSON (unreadable ⇒ treat as stale) → refuse only if holder pid is alive AND lock is younger than 15 min → otherwise steal by rm+recreate (a concurrent stealer losing the re-create race just returns false). Release removes the file ONLY if `pid === process.pid && workflowId matches` — never touch another workflow's lock.
**Invariant:** The lock must be a filesystem atomic primitive, NOT state.json — `start` (detached child), `daemon` (separate process), and `orchestrate` (another process) coordinate through it. A dead-pid or >15min-old lock is stolen, so a crashed executor cannot wedge the platform forever. Callers MUST release in a `finally`.
**Probe:** `scripts/lib/platform-lock.test.ts` — `acquireLock succeeds when free, then blocks a second live holder` (:13), `steals a stale lock whose pid is dead` (:20), `steals an unreadable/corrupt lock` (:28), `releaseLock removes only a lock this process owns` (:36), `releaseLock leaves a lock owned by a different workflow intact` (:43). Note the test writes `acquiredAt: 'x'` — an unparseable timestamp makes `isStale` false, so the steal in those tests comes from the dead pid alone.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "acquireLock releaseLock platform", limit: 10, fields: ["signature", "file"] });
```

## Verdict
Adopt the wx-atomic lock with pid-liveness + age-based stale stealing and ownership-checked release. Adapt lock dir location, stale timeout to your longest task. Omit none of it — the subtle parts (EPERM-means-alive, unreadable-JSON-means-stale, age guard against pid reuse) are exactly what a naive port gets wrong.
