<!-- capsule-v2 -->
# Atomic lock coordinator — cross-process SQLite-backed locks with token fencing and stale takeover

**Source:** pi-hermes-memory (MIT, `main@26f0acaa7741a81ea28eb992ab7ffcfdb7b50a0c`); Codebase Memory `pi-hermes-memory`. **Question:** How does an agent coordinate exclusive access to a shared resource across processes — acquiring a lock atomically, fencing stale tokens, taking over wedged-but-alive holders, renewing long-running leases, and garbage-collecting dead holders — without leaking connections?

## AtomicLockCoordinator
**Path/Symbol:** `src/store/atomic-lock-coordinator.ts:AtomicLockCoordinator` (class, 111–375); `tryAcquire` (127–193), `renew` (221–240), `release` (242–253), `isCurrentOwner` (205–209), `sweepDeadLocks` (272–293), `holderIsGone` (296–301), `open` (322–355), `shared` (366–374).
**Signature:** `new AtomicLockCoordinator(dbPath, {pid?, incarnation?, probeIncarnation?})`; `tryAcquire(key, {staleMs}) → AtomicLockLease | null`; `AtomicLockLease = { token, release(), renew(): boolean }`.
**Data Shape:** lock rows in a `locks` table: `(lock_key TEXT PRIMARY KEY, token TEXT, pid INTEGER, incarnation TEXT, acquired_at INTEGER)`. `incarnation` is the process start-time (Linux `/proc/<pid>/stat` field 22, else `ps -o lstart=` / PowerShell StartTime), used to distinguish a reused PID from the original holder. `AtomicLockLease.renew()` refreshes `acquired_at` and returns `false` once the lease has been taken over.

### Decisive source
```ts
// tryAcquire (127-193): BEGIN IMMEDIATE, read owner, steal-or-insert, COMMIT
db.exec('BEGIN IMMEDIATE');
try {
  const owner = db.prepare('SELECT token, pid, incarnation, acquired_at FROM locks WHERE lock_key = ?').get(key);
  if (!owner) { db.prepare('INSERT INTO locks ...').run(key, token, this.pid, this.incarnation, now); acquired = true; }
  else {
    const observedIncarnation = this.probeIncarnation(owner.pid);
    const alive = observedIncarnation !== null || processIsAlive(owner.pid);
    const sameIncarnation = alive && owner.incarnation !== null && observedIncarnation !== null && owner.incarnation === observedIncarnation;
    const unknownIncarnation = alive && (owner.incarnation === null || observedIncarnation === null);
    // stale takeover: held longer than staleMs regardless of liveness (wedged, not dead)
    const stale = options.staleMs > 0 && now - owner.acquired_at >= options.staleMs;
    if (stale || (!sameIncarnation && !unknownIncarnation)) {
      db.prepare('UPDATE locks SET token=?, pid=?, incarnation=?, acquired_at=? WHERE lock_key=? AND token=?')
        .run(token, this.pid, this.incarnation, now, key, owner.token);
      acquired = true;
    }
  }
  db.exec('COMMIT');
} catch (error) { try { db.exec('ROLLBACK'); } catch { this.discardCachedDb(); } throw error; }
if (!acquired) return null;
return { token, release: () => this.release(key, token), renew: () => this.renew(key, token) };

// renew (221-240): token-fenced — only refreshes if still the owner, else returns false
const owner = db.prepare('SELECT token FROM locks WHERE lock_key = ?').get(key);
const owned = owner?.token === token;
if (owned) db.prepare('UPDATE locks SET acquired_at = ? WHERE lock_key = ? AND token = ?').run(Date.now(), key, token);
return owned;

// sweepDeadLocks (272-293): delete rows whose holder process is gone (fenced on token+acquired_at)
// holderIsGone (296-301): pid dead AND incarnation probe null
// shared (366-374): one coordinator per resolved dbPath so connections are not leaked
```

**Flow:** (1) `tryAcquire` opens the lock DB, sweeps dead locks (once per 60s), then `BEGIN IMMEDIATE` and reads the owner row. (2) If absent, insert and acquire. If present, decide takeover: a lease is reclaimable once held longer than `staleMs` (regardless of liveness — the holder may be wedged), or when the incarnation differs (PID reused). (3) On success return a lease with `release` and `renew`. (4) `renew` beats the lease so a legitimately long holder (e.g. a consolidation child) never loses it; it is token-fenced so a taken-over lease returns `false`. (5) `release` deletes the owned row, retrying 3× then deferring to the next same-process acquisition. (6) `isCurrentOwner` is a fencing check for destructive operations that lack their own compare-and-swap.

**Invariant:** a lease is token-fenced (only the current token can renew/release); a stale-but-alive holder is reclaimable after `staleMs`; a reused PID is not mistaken for the original holder via incarnation probing; dead holders are GC'd; one coordinator per DB path so connections are not leaked.

**Probe:** `tests/store/atomic-lock-coordinator.test.ts` — `cannot release a successor with a stale ownership token` (:11), `takes over a reused PID without taking over the original incarnation` (:62), `reclaims an alive unknown-incarnation owner after staleMs elapses` (:113), `fences stale original tokens after a staleMs takeover` (:171), `keeps a beating holder out of reach of a stale takeover` (:279), `refuses to renew a lease that was already taken over` (:314), `collects lock rows whose holder process is gone` (:348). Coverage caveat: `tests/` is excluded from the index by design, so probes are source-grounded from the on-disk test files.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-hermes-memory", query: "AtomicLockCoordinator tryAcquire renew release isCurrentOwner sweepDeadLocks", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the SQLite `BEGIN IMMEDIATE` lock-row pattern, token fencing, pid+incarnation liveness probing, stale takeover, heartbeat renew, dead-lock GC, and the shared-per-path coordinator. Adapt the lock table schema, the stale/grace/interval constants, and the incarnation probe (Linux `/proc` vs `ps` vs PowerShell) to the host. Omit the `isCurrentOwner` fencing hook unless you have destructive renames without their own compare-and-swap.
