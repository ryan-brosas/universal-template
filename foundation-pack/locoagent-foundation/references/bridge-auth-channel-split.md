<!-- capsule-v2 -->
# Bridge env-var auth split — per-instance closures vs the process-wide session token

**Source:** LocoAgent MIT `main@c01bb3f8a7b06a0db9f697c5bea485947959d226`; Codebase Memory `locoagent`. **Question:** When a library reads its auth from a process-wide environment variable, how do you serve multiple concurrent sessions without them stomping each other?

## Path/Symbol
**Path/Symbol:** `src/bridge/replBridgeTransport.ts` — getAuthToken option + env-var fallback (:148-155, :169-181); hazard docstring in `src/bridge/remoteBridgeCore.ts` (:229-235: "keeps the worker JWT out of process.env.CLAUDE_CODE_SESSION_ACCESS_TOKEN, which mcp/client.ts reads ungatedly and would otherwise send to user-configured ws/http MCP servers"); consumer-side refresh in `src/bridge/replBridge.ts` onConnect (:1218-1229: v1-only re-push, v2 skips to protect the JWT's session_id claim).
**Signature:** `getAuthToken?: () => string | undefined` — when present, CCRClient+SSETransport read headers from THIS closure; when absent, the transport writes ingressToken to the process-wide env var before touching the network.
**Data Shape:** two credential classes sharing one env slot historically: OAuth access tokens (v1 Session-Ingress) and session-bound worker JWTs (v2) — plus every unrelated reader of the same var.

### Decisive source
```ts
// Per-instance closure — keeps the worker JWT out of
// process.env.CLAUDE_CODE_SESSION_ACCESS_TOKEN, which mcp/client.ts
// reads ungatedly and would otherwise send to user-configured ws/http
// MCP servers. Frozen-at-construction is correct: transport is fully
// rebuilt on refresh (rebuildTransport below).
getAuthToken: () => credentials.worker_jwt,
...
// v2 skips this — createV2ReplTransport already stored the JWT,
// and overwriting it with OAuth would break subsequent /worker/*
// requests (session_id claim check).
if (!useCcrV2) {
  const freshToken = getOAuthToken()
  if (freshToken) updateSessionIngressAuthToken(freshToken)
}
```

**Flow:** single-session legacy path keeps the env-var contract (updateSessionIngressAuthToken writes it; transports and HybridTransport's refreshHeaders read it). Multi-session or secret-bearing paths pass `getAuthToken` so each transport instance carries its OWN source; v2 freezes the closure over the CURRENT credentials object and relies on full transport rebuild (not mutation) for rotation. The v1/v2 asymmetry at onConnect is the trap: refreshing the env var with OAuth after a v2 transport stored the JWT would fail every /worker/* call (register_worker.go validates the session_id claim OAuth lacks).

**Invariant:** (1) Any credential readable by UNRELATED subsystems must not live in a shared global — inject a closure. (2) Frozen-at-construction + rebuild-on-rotation beats in-place mutation: no partial-update windows. (3) Refresh points must be version-aware: pushing a fresh OAuth token into a v2 transport's auth channel corrupts it. (4) The env-var path remains the default for single-session callers — don't break their contract while adding the escape hatch.

**Probe:** coverage caveat — no upstream unit tests. Deterministic pins: `grep -n "mcp/client.ts" src/bridge/remoteBridgeCore.ts` (:230-231); `grep -n "overwriting it with OAuth" src/bridge/replBridge.ts` (:1221-1223); `grep -n "stomps across sessions" src/bridge/replBridgeTransport.ts` (:152); graph resolves `locoagent.src.bridge.replBridgeTransport.createV2ReplTransport` :119-370 line-exact.

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "getAuthToken updateSessionIngressAuthToken CLAUDE_CODE_SESSION_ACCESS_TOKEN createV2ReplTransport", limit: 5, fields: ["signature","name","file"] });
```

## Verdict
Adopt the optional-closure-with-env-default pattern for any library whose auth currently rides a process global. Adapt variable names; keep the frozen-closure + rebuild semantics — mutating shared auth state per-session is the bug class this capsule exists to prevent.
