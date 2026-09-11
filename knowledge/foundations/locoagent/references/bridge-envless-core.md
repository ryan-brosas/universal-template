<!-- capsule-v2 -->
# Env-less bridge core — direct OAuth→worker_jwt exchange with transport rebuild on every refresh

**Source:** LocoAgent MIT `main@c01bb3f8a7b06a0db9f697c5bea485947959d226`; Codebase Memory `locoagent`. **Question:** How do you drop a poll/dispatch layer entirely and hold a long-lived session directly against worker endpoints without breaking on credential rotation?

## Path/Symbol
**Path/Symbol:** `src/bridge/remoteBridgeCore.ts` — `initEnvLessBridgeCore` (:140-887): 5-step handshake docstring (:10-29), authRecoveryInFlight double-claim guard (:330-377 + :530-535), rebuildTransport (:477-527), recoverFromAuthFailure (:530-590), flushHistory trailing-user state push (:624-656), teardown ordering (:664-745: result write → archive → close; archive timeout capped 2000ms under gracefulShutdown's 2s race), `withRetry` exp+jitter (:892-913), archiveSession compat retag (:963-1008); `src/bridge/codeSessionApi.ts` — `createCodeSession` (bridge:{} oneof signal :41), `fetchRemoteCredentials` (:93-168).
**Signature:** `initEnvLessBridgeCore(params) → ReplBridgeHandle | null`; each `POST /bridge` returns `{worker_jwt, api_base_url, expires_in, worker_epoch}` — **the /bridge call IS the register** (epoch bumps server-side per call).
**Data Shape:** ConnectCause = 'initial'|'proactive_refresh'|'auth_401_recovery' (telemetry discriminator set before wireTransport, read async by onConnect).

### Decisive source
```ts
// Each /bridge call bumps epoch server-side. Both refresh paths must
// rebuild the transport with the new epoch — a JWT-only swap leaves the
// old CCRClient heartbeating stale epoch → 409. SSE resumes from the old
// transport's high-water-mark seq-num so no server-side replay.
// Caller MUST set authRecoveryInFlight = true before calling (synchronously,
// before any await) and clear it in a finally.
...
flushGate.start()
try {
  const seq = transport.getLastSequenceNum()
  transport.close()
  transport = await createV2ReplTransport({...})
```

**Flow:** create session (OAuth, no env_id) → fetch credentials (OAuth+trusted-device header) → build v2 transport with **per-instance `getAuthToken: () => credentials.worker_jwt` closure** (frozen at construction — the process-wide env-var path would leak the JWT to user-configured MCP servers that read it ungated) → refresh scheduler fires `expires_in - buffer` early → BOTH proactive-refresh and 401-recovery paths claim `authRecoveryInFlight` synchronously before any await (laptop wake fires both ~simultaneously; two /bridge fetches would double-bump epoch so the first rebuild 409s) → rebuild closes old transport, resumes SSE from captured seq, re-wires callbacks, re-schedules refresh, drains the gate queued during rebuild. Teardown: reportState idle → fire-and-forget result message → archive (its 100-500ms latency IS the uploader drain window) → close LAST (close-before-archive drops the result).

**Invariant:** (1) JWT-only swaps are forbidden — epoch lives in the transport, so every refresh rebuilds it. (2) The recovery flag must be claimed synchronously pre-await; checking inside the async body is too late to prevent the second fetch. (3) initialFlushDone resets on 401 recovery because writeBatch may have silently no-op'd on the closed uploader. (4) v2 never filters by previouslyFlushedUUIDs (fresh session every enable) while v1 clears the set on fresh creation — symmetric fixes for the same duplicate-history hazard.

**Probe:** coverage caveat — no upstream unit tests. Deterministic pins: `grep -n "double epoch bump" src/bridge/remoteBridgeCore.ts` (:332-333); `grep -n "mcp/client.ts" src/bridge/remoteBridgeCore.ts` (:230); `grep -n "close-before-archive drops the result" src/bridge/remoteBridgeCore.ts` (:676); graph resolves `locoagent.src.bridge.remoteBridgeCore.initEnvLessBridgeCore` :140-887 line-exact.

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "initEnvLessBridgeCore rebuildTransport recoverFromAuthFailure fetchRemoteCredentials authRecoveryInFlight", limit: 6, fields: ["signature","name","file"] });
```

## Verdict
Adopt the handshake ladder + synchronous-recovery-claim pattern for any direct-to-worker session protocol. Adapt the credential endpoint; omit mirror-mode outboundOnly if you have no event-fanout twin. Porting trap: swapping only the JWT on refresh — the stale epoch 409s within one heartbeat.
