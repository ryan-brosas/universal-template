<!-- capsule-v2 -->
# Resident host file protocol — how do you run a durable agent supervisor that outlives the UI, with crash-safe requests and honest indeterminate outcomes?

**Source:** pi-fabric MIT `feat/veda-runner@4874ac3a`; Codebase Memory `pi-fabric`. **Question:** what directory protocol lets a headless process own actors/agents across Main restarts without ever double-processing a request?

## Rename-claim + processing-dir recovery + pid/token locks
**Path/Symbol:** `src/residency/host.ts` — `#pollRequests` (:442-466), `#processRequest` (:488-576), `#recoverInterruptedRequests` (:578-597), `#acquireLock`/:`#releaseLock` (:599-630), `#checkIdle` (:468-486), config jail :99-101.
**Signature:** `ResidentHost.start()/close()`; request/response = JSON files named `<requestId>.json` in `requests/ → processing/ → responses/`.
**Data Shape:** validated config `{format, rootId, sessionId, cwd, projectRoot, meshRoot, actorRoot, residencyRoot, ...binaries}`; owner file `{format, hostId, pid, token, startedAt, readyAt}`; lock `{token, pid}` via exclusive-create (`wx`) 0600 file.

### Decisive source
```ts
// claim: atomic rename is the dequeue
try { fs.renameSync(source, processing); } catch { continue; }   // lost race ⇒ skip
// recovery: anything found in processing/ after a restart gets an HONEST failure
const response = { ok: false,
  error: "Fabric residency outcome is indeterminate after resident host restart" };
atomicWrite(path.join(responsesPath, entry), response);
// lock: stale-owner recovery requires BOTH dead-pid and EEXIST path; release is token-checked
if (lock?.token === this.#token) fs.rmSync(this.#lockPath, { force: true });
```

**Flow:** start validates config (residencyRoot must BE the config's parent — no pointer escape) and mesh-enabled → acquire lock (owner.json liveness check first, then wx-create; stale EEXIST recovered only when recorded pid is dead) → recover interrupted requests into explicit indeterminate responses → poll every 50ms: rename each request into `processing/` (the atomic claim), execute spawn/foreground/cleanup/remove against agents+actors (durable spawns REJECT session-coupled fields: sessionSeed/sessionFile/actorId/meshRoot/images — "only its public task and run settings"), write response, delete processing entry → idle-exit after 30s with zero active actors, running agents, AND pending requests.
**Invariant:** at-most-once *processing* with exactly-once *answers*: a crash mid-request yields a visible "indeterminate" response rather than silence or silent re-execution; lock deletion and owner deletion are both guarded by the random per-instance token so a recycled pid cannot delete a successor's files.
**Probe:** `tests/residency.test.ts:179` ("keeps a durable actor responsive after its originating Main closes", timeout 20s), :323 (passive delivery queued until resume), :410 ("completes and cleans a durable agent after its originating Main closes") — full two-process harness.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-fabric", query: "ResidentHost recoverInterruptedRequests processing renameSync", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the three-directory rename-claim protocol and token-guarded locks for any out-of-process supervisor; adapt the command set to your operations; omit herdr-style sockets if files are your only IPC. Direct e2e tests exercise real cross-process flows — no coverage caveat.
