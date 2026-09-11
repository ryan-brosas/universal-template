<!-- capsule-v2 -->
# Bridge URL ladder — how do you route browser traffic between local native sockets and a cloud WebSocket bridge without stranding third-party users on the experimental path?

**Source:** LocoAgent MIT `main@c01bb3f8a7b06a0db9f697c5bea485947959d226`; Codebase Memory `locoagent`. **Question:** What gates decide native-messaging vs remote-bridge transport, and what identity/token plumbing does each need?

## chrome-bridge-url-ladder
**Path/Symbol:** `src/utils/claudeInChrome/mcpServer.ts` (`getChromeBridgeUrl` :51-72, `isLocalBridge` :74-79, `bridgeConfig` :139-150, `PERMISSION_MODES` :36-40).
**Signature:** `getChromeBridgeUrl(): string | undefined` — `undefined` = use the local native socket; otherwise a `ws(s)://` URL.
**Data Shape:** ladder inputs: `USER_TYPE === 'ant'`, feature flag `tengu_copper_bridge`, env `USE_LOCAL_OAUTH`/`LOCAL_BRIDGE` → `ws://localhost:8765`, `USE_STAGING_OAUTH` → staging wss, default prod wss. `bridgeConfig = {url, getUserId: oauthAccount.accountUuid, getOAuthToken: accessToken ?? '', devUserId?}`.

### Decisive source
```ts
const bridgeEnabled =
  process.env.USER_TYPE === 'ant' ||
  getFeatureValue_CACHED_MAY_BE_STALE('tengu_copper_bridge', false)

if (!bridgeEnabled) {
  return undefined
}
```
plus permission-mode validation (:91-103): an unknown `CLAUDE_CHROME_PERMISSION_MODE` value logs a warning listing valid values and leaves the mode UNSET rather than guessing.

**Flow:** ant users always get the bridge; externals only behind the flag; env overrides pick local/staging endpoints for development. When bridged, requests carry the user's OAuth token + account UUID so the extension can verify account match (`onAuthenticationError` message tells users to log both CLI and extension into the SAME claude.ai account); when not bridged, everything flows over the per-PID Unix socket. `skip_all_permission_checks` mode is granted ONLY when the session itself runs with bypass-permissions (set by setup.ts from `getSessionBypassPermissionsMode()`).
**Invariant:** the bridge is capability-gated BEFORE endpoint selection (flag first, env second) — inverting that would let a stray env var expose internal infrastructure to external users; token accessor degrades to empty string (never throws) so a missing login surfaces as the extension's auth-error callback instead of a crash.
**Probe:** no upstream test. Deterministic pins: `grep -n "tengu_copper_bridge" src/utils/claudeInChrome/mcpServer.ts` → :54; `grep -n "bridge-staging" src/utils/claudeInChrome/mcpServer.ts` → :68.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "getChromeBridgeUrl bridgeConfig", limit: 10 });
```

## Verdict
Adopt gate→endpoint ordering and the undefined-means-local contract. Adapt endpoints/flags. Omit the specific feature-flag names. Coverage caveat: no unit tests upstream.
