<!-- capsule-v2 -->
# Bridge entitlement gates — subscriber checks, dead-token backoff, and positive feature gating

**Source:** LocoAgent MIT `main@c01bb3f8a7b06a0db9f697c5bea485947959d226`; Codebase Memory `locoagent`. **Question:** How do you gate a subscription feature with actionable failures, avoid burning API calls on provably-dead tokens, and keep tree-shaking intact?

## Path/Symbol
**Path/Symbol:** `src/bridge/bridgeEnabled.ts` — `isBridgeEnabled` (:28-36), `isBridgeEnabledBlocking` (:50-55, cached-true fast path vs ≤5s slow path), `getBridgeDisabledReason` (:70-87, ordered diagnostics), pre-config try/catch swallow (:89-116), `checkBridgeMinVersion` (:160-173), `getCcrAutoConnectDefault` (:185-189); `src/bridge/initReplBridge.ts` gate ladder (:134-241) incl. cross-process backoff 2a (:169-187), proactive refresh 2b rationale (:189-201), dead-token detection 2c (:203-240).
**Signature:** `isBridgeEnabledBlocking(): Promise<boolean>`; `getBridgeDisabledReason(): Promise<string | null>`.
**Data Shape:** persisted backoff state in global config: `{bridgeOauthDeadExpiresAt, bridgeOauthDeadFailCount}` — keyed by the token's expiresAt (content-addressed).

### Decisive source
```ts
// Positive ternary pattern — see docs/feature-gating.md.
// Negative pattern (if (!feature(...)) return) does not eliminate
// inline string literals from external builds.
return feature('BRIDGE_MODE')
  ? isClaudeAISubscriber() &&
      getFeatureValue_CACHED_MAY_BE_STALE('tengu_ccr_bridge', false)
  : false
...
// Check actual expiry instead: past-expiry AND refresh-failed → truly dead.
if (tokens && tokens.expiresAt !== null && tokens.expiresAt <= Date.now()) {
  ... saveGlobalConfig(c => ({ ...c,
    bridgeOauthDeadExpiresAt: deadExpiresAt,
    bridgeOauthDeadFailCount:
      c.bridgeOauthDeadExpiresAt === deadExpiresAt
        ? (c.bridgeOauthDeadFailCount ?? 0) + 1 : 1 }))
```

**Flow:** init ladder order is load-bearing: runtime gate → OAuth presence (BEFORE policy check so console-auth users get "/login" not a misleading policy error) → org policy → (unless dev-token override) cross-process dead-token skip → proactive refresh → post-refresh still-expired ⇒ persist dead token. The backoff counter tolerates ≤2 transient refresh failures; at 3 matches-by-expiresAt the process skips silently. A /login mints a new expiresAt which stops matching WITHOUT any explicit clear. GrowthBook's org-targeting needs organizationUUID from the profile scope — setup-tokens lack it, so `getBridgeDisabledReason` names that exact failure ("full-scope login token") instead of a dead-end "not enabled".

**Invariant:** (1) Feature-gate reads must use the positive-ternary shape or bundlers ship flag-name strings to external builds. (2) Config reads before enableConfigs() throw — entitlement helpers wrap ALL config-touching auth calls in try/catch returning false/undefined (pre-config no token can exist anyway). (3) Dead-token detection requires past-expiry AND failed refresh — a buffered "should refresh soon" check falsely trips on transient blips while the token still works. (4) Diagnostics are ordered from most actionable (subscription → scope → org → rollout) so each message names its own fix.

**Probe:** coverage caveat — no upstream unit tests. Deterministic pins: `grep -n "does not eliminate" src/bridge/bridgeEnabled.ts` (:30-31); `grep -n "2,879 such 401s/day" src/bridge/initReplBridge.ts` (:210); `grep -n "Config accessed before allowed" src/bridge/bridgeEnabled.ts` (:91); graph resolves `locoagent.src.bridge.bridgeEnabled.getBridgeDisabledReason` :70-87 line-exact.

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "isBridgeEnabledBlocking getBridgeDisabledReason checkBridgeMinVersion isCseShimEnabled", limit: 6, fields: ["signature","name","file"] });
```

## Verdict
Adopt the gate ladder + content-addressed dead-token backoff wholesale for any subscription-gated connectivity feature. Adapt flag names/copy; omit mirror/auto-connect defaults if you have no such modes.
