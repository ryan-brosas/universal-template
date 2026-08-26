<!-- capsule-v2 -->
# Session-ID tag compat — how do cse_* and session_* costumes coexist safely?

**Source:** LocoAgent MIT `main@c01bb3f8a7b06a0db9f697c5bea485947959d226`; Codebase Memory `locoagent`. **Question:** How do you compare and translate tagged session IDs when the compat layer returns one prefix to clients but the infrastructure layer uses another for the same UUID?

## Path/Symbol
**Path/Symbol:** `src/bridge/sessionIdCompat.ts` — `setCseShimGate` (:21-23), `toCompatSessionId` (:38-42), `toInfraSessionId` (:54-57); `src/bridge/workSecret.ts` — `sameSessionId` (:62-73); gate source `src/bridge/bridgeEnabled.ts` — `isCseShimEnabled` (:141-148, default **true**).
**Signature:** `toCompatSessionId(id): string` (cse_*→session_*, gated, no-op otherwise); `toInfraSessionId(id): string` (session_*→cse_*, UNGATED); `sameSessionId(a,b): boolean`.
**Data Shape:** module-level `_isCseShimEnabled: (() => boolean) | undefined` — injected via setter because a static import of bridgeEnabled→growthbook→config is banned from the sdk.mjs bundle; unset gate ⇒ shim ACTIVE.

### Decisive source
```ts
// Worker endpoints (/v1/code/sessions/{id}/worker/*) want `cse_*`; that's
// what the work poll delivers. Client-facing compat endpoints
// (/v1/sessions/{id}, /v1/sessions/{id}/archive, /v1/sessions/{id}/events)
// want `session_*` — compat/convert.go:27 validates TagSession. Same UUID,
// different costume. No-op for IDs that aren't `cse_*`.
export function toCompatSessionId(id: string): string {
  if (!id.startsWith('cse_')) return id
  if (_isCseShimEnabled && !_isCseShimEnabled()) return id
  return 'session_' + id.slice('cse_'.length)
}
```

**Flow:** work poll delivers infra-tagged IDs; every client-facing call (archive/PATCH-title/events URL) re-tags to compat; every environments-layer call (`/bridge/reconnect`) re-tags to infra — the pointer stores what createSession returned (`session_*`) while reconnect under `ccr_v2_compat_enabled` looks up by `cse_*`, so callers try BOTH candidates (`[resumeSessionId, toInfraSessionId(...)]`). Comparison strips everything after the LAST underscore and requires body ≥4 chars, which handles `{tag}_{body}` AND `{tag}_staging_{body}` and never false-matches bare UUIDs.

**Invariant:** (1) Directional gating is load-bearing: the compat direction honors a kill switch (flip server-side tagging, then disable shim), the infra direction does NOT — reconnect must find the session regardless of rollout state. (2) A missing/unset gate defaults the shim ON, matching `isCseShimEnabled()`'s own default. (3) bridgeMain caches the compat ID per session (`sessionCompatIds`) so a MID-SESSION gate flip can't split logger keys from archive calls; remoteBridgeCore instead computes fresh per call because its compatId is only a URL segment with no in-memory twin. (4) Never compare tagged IDs with `===` across layers.

**Probe:** coverage caveat — no upstream unit tests. Deterministic pins: `grep -n "Same UUID," src/bridge/sessionIdCompat.ts` (:32 and :52); `grep -n "aBody.length >= 4 && aBody === bBody" src/bridge/workSecret.ts` (:72); `grep -n "defaults to active" src/bridge/sessionIdCompat.ts` (:12); graph resolves `locoagent.src.bridge.sessionIdCompat.toCompatSessionId` :38-42 line-exact.

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "toCompatSessionId toInfraSessionId sameSessionId setCseShimGate", limit: 5, fields: ["signature","name","file"] });
```

## Verdict
Adopt the dual-costume translation + UUID-body comparison wholesale for any system where a compat facade renames resource IDs. Adapt candidate-list retry ([compat, infra]) wherever a stored ID's provenance predates the gateway.
