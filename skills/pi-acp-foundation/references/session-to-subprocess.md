<!-- capsule-v2 -->
# Session↔subprocess mapping — one ACP session per pi subprocess, single live subprocess

**Source:** pi-acp-jetbrain MIT `main@27aac05f`; Codebase Memory `pi-acp`. **Question:** How does the adapter map ACP sessions to pi subprocesses, keep only one live subprocess per client window, and restore a session without leaking or double-spawning?

## Session mapping
**Path/Symbol:** `src/acp/session.ts:SessionManager` (154-291) + `src/acp/agent.ts:PiAcpAgent.restoreSession` (232-301) + `newSession` (348-527).
**Signature:** `SessionManager.create(params): Promise<PiAcpSession>`; `PiAcpAgent.restoreSession(sessionId, opts?): Promise<PiAcpSession>`.
**Data Shape:** `SessionManager` holds `sessions: Map<sessionId, PiAcpSession>`, a `closing` map of in-flight close promises, and a `SessionStore`. `PiAcpAgent` holds `restoringSessions: Map<sessionId, Promise<PiAcpSession>>` for in-flight restore dedup.

### Decisive source
```ts
// PiAcpAgent.restoreSession
const existing = this.sessions.maybeGet(sessionId)
if (existing) return existing
const inFlight = this.restoringSessions.get(sessionId)
if (inFlight) return inFlight
const restorePromise = (async () => {
  const stored = this.findStoredSession(sessionId)   // SessionStore OR pi-session discovery
  if (!stored) throw RequestError.invalidParams(`Unknown sessionId: ${sessionId}`)
  const { bridge, settings } = await this.startBridge(opts?.mcpServers ?? [], sessionId, cwd)
  const proc = await PiRpcProcess.spawn({ cwd, sessionPath: stored.sessionFile, ... })
  const session = this.sessions.getOrCreate(sessionId, { cwd, proc, bridge, ... })
  if (bridgeSettings.extensionPaths.length) await this.waitForBridgeReady(bridge, bridgeSettings)
  this.store.upsert({ sessionId, cwd, sessionFile: stored.sessionFile })
  return session
})()
this.restoringSessions.set(sessionId, restorePromise)
try { return await restorePromise } finally { this.restoringSessions.delete(sessionId) }
```
```ts
// newSession policy
await this.closeManagedSessionsExcept(session.sessionId)   // keep only ONE live pi subprocess
```

**Flow:** `session/new` → `SessionManager.create` spawns a pi subprocess, reads `get_state` for the real `sessionId`/`sessionFile`, upserts the store, registers the session. `session/prompt`/`loadSession`/`setSessionMode`/`setSessionConfigOption` all call `restoreSession` which returns the live session, dedups in-flight restores, or spawns a fresh subprocess bound to the stored session file. After every new/load, `closeManagedSessionsExcept` tears down all other sessions so a client window holds exactly one live pi subprocess.

**Invariant:** Only one pi subprocess stays alive per ACP connection (avoids leaking subprocesses when clients open new sessions without closing old ones); a concurrent restore of the same id reuses the in-flight promise; a failed `newSession` cleans up the spawned subprocess and deletes the session file.

**Probe:** `test/unit/session-restore.test.ts` ("PiAcpAgent: prompt auto-restores a missing session from SessionStore", "PiAcpAgent: cancel ignores stale session IDs without spawning a restore process") — pins auto-restore and no-spawn-on-stale-cancel.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-acp", query: "restoreSession SessionManager closeAllExcept", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the 1:1 session↔subprocess mapping, the single-live-subprocess policy, in-flight restore dedup, and failure cleanup. Adapt the session-file lookup (SessionStore vs pi-session discovery) and the `--session <path>` spawn arg to the host. Omit the `closeManagedSession`/`closeManagedSessionsExcept` duck-typed fallbacks (test seams).
