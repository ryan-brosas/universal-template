<!-- capsule-v2 -->
# mkdir-lock mutex — cross-process mutual exclusion without flock: when may a waiter steal a held lock?

**Source:** Cline Apache-2.0 `main@4f836ae7d0ed29ece7ef4a2a478deb470fdd056e`; Codebase Memory `cline`. **Question:** How do unrelated processes serialize discovery/daemon mutations on a plain filesystem, and when is stealing an existing lock safe?

## mkdir as test-and-set; liveness+age theft; init-window respect
**Path/Symbol:** `sdk/packages/core/src/hub/discovery/index.ts:463-533` (`withHubLock`, `withHubDiscoveryMutationLock`); singleton layer `hub/discovery/instance-lock.ts` (`HubInstanceLock.acquire → HubLockHeldError`).
**Signature:** `withHubLock<T>(lockBasis, label, callback) → Promise<T>`; lock dir = `getHubLockDir(lockBasis)`; owner record `{pid, acquiredAt}` in `owner.json`.
**Data Shape:** Lock = directory (mkdir EEXIST = "held"); bounded wait `HUB_STARTUP_LOCK_WAIT_MS`, poll `HUB_STARTUP_LOCK_POLL_MS`, max age `HUB_STARTUP_LOCK_MAX_AGE_MS`.

### Decisive source
```ts
try { await mkdir(lockDir, { recursive: false }); }  // atomic test-and-set
catch (error) {
    if (code !== "EEXIST") throw error;
    const record = await readHubLockRecord(lockDir);
    if (!record) {
        // The winner creates the directory before it can publish owner.json.
        // Do not steal that initialization window. A genuinely abandoned
        // empty lock is reclaimed only after the bounded wait.
        if (Date.now() >= deadline) { await removeHubLock(lockDir); continue; }
        await sleep(HUB_STARTUP_LOCK_POLL_MS); continue;
    }
    const lockAge = Date.now() - Date.parse(record.acquiredAt);
    if (!isPidAlive(record.pid) || lockAge > HUB_STARTUP_LOCK_MAX_AGE_MS) {
        await removeHubLock(lockDir); continue;   // steal dead/stale holder
    }
    if (Date.now() >= deadline) { throw new Error(`Timed out waiting for hub ${label} lock ${lockDir}`); }
    await sleep(HUB_STARTUP_LOCK_POLL_MS); continue;
}
try { await writeFile(join(lockDir, "owner.json"), ...); return await callback(); }
finally { await removeHubLock(lockDir); }
```

**Flow:** loop { mkdir wins ⇒ write owner.json, run callback, remove lock in finally } | EEXIST ⇒ no owner.json yet = winner's initialization window, never stolen before deadline | owner.json present ⇒ steal iff holder PID is dead OR age > max; else sleep-poll until deadline ⇒ timeout error naming the lock path. A second, non-stealing singleton layer exists: `HubInstanceLock.acquire` fails fast with typed `HubLockHeldError` (idempotent release, scoped per discovery path) so one process can claim "the hub instance" outright.
**Invariant:** Mutual exclusion holds because directory creation is the single atomic decision point; theft requires *positive evidence* (dead PID or expired age), never mere waiting; a crashed holder cannot wedge the system past MAX_AGE; every acquire removes its own lock exactly once.
**Probe:** `grep -cF 'await mkdir(lockDir, { recursive: false });' sdk/packages/core/src/hub/discovery/index.ts` → 1; `grep -cF 'if (!isPidAlive(record.pid) || lockAge > HUB_STARTUP_LOCK_MAX_AGE_MS) {' ...` → 1; `grep -cF '// Do not steal that initialization window.' ...` → 1. Direct tests: `discovery/instance-lock.test.ts` ("grants exclusive ownership and refuses a second acquirer", "release is idempotent", "scopes locks per discovery path").

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "cline", query: "withHubLock mkdir lock pid alive steal", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt mkdir-EEXIST mutex with evidence-gated theft and the two-layer split (cooperative serialized mutation vs fail-fast singleton claim). Adapt timeouts/poll intervals and owner-record fields; keep the init-window rule — it is what makes owner.json publication race-free. Omit Cline's specific hub paths. Runner-BLOCKED here; probes green.
