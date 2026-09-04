<!-- capsule-v2 -->
# Bridge config resolution — ant-only override layers over the OAuth store

**Source:** LocoAgent MIT `main@c01bb3f8a7b06a0db9f697c5bea485947959d226`; Codebase Memory `locoagent`. **Question:** How do you consolidate dev-only environment overrides that were copy-pasted across a dozen files into one resolution layer without letting them leak into production paths?

## Path/Symbol
**Path/Symbol:** `src/bridge/bridgeConfig.ts` — whole file (48L): `getBridgeTokenOverride` (:18-24), `getBridgeBaseUrlOverride` (:27-32), `getBridgeAccessToken` (:38-40), `getBridgeBaseUrl` (:46-48); consumers listed in docstring (:3-6: inboundAttachments, BriefTool/upload, bridgeMain, initReplBridge, remoteBridgeCore, daemon workers, /rename, /remote-control).
**Signature:** `getBridgeAccessToken(): string | undefined` (undefined = not logged in); `getBridgeBaseUrl(): string` (ALWAYS returns a URL).
**Data Shape:** two-layer pattern: `*Override()` returns the env var gated on `USER_TYPE === 'ant'` or undefined; non-Override versions fall through to real auth/config.

### Decisive source
```ts
/**
 * Shared bridge auth/URL resolution. Consolidates the ant-only
 * CLAUDE_BRIDGE_* dev overrides that were previously copy-pasted across
 * a dozen files ...
 *
 * Two layers: *Override() returns the ant-only env var (or undefined);
 * the non-Override versions fall through to the real OAuth store/config.
 * Callers that compose with a different auth source (e.g. daemon workers
 * using IPC auth) use the Override getters directly.
 */
export function getBridgeTokenOverride(): string | undefined {
  return (
    (process.env.USER_TYPE === 'ant' &&
      process.env.CLAUDE_BRIDGE_OAUTH_TOKEN) ||
    undefined
  )
}
```

**Flow:** default callers read `getBridgeAccessToken()` (override ?? keychain) and `getBridgeBaseUrl()` (override ?? OAuth config). Composing callers — daemon workers whose auth arrives via IPC, or remoteBridgeCore's `fetchRemoteCredentials` wrapper which must pin api_base_url to the OVERRIDDEN base while the server returns a prod URL — consume the Override getters directly and layer their own fallback. The override deliberately bypasses the keychain entirely: an expired keychain token must not block a dev bridge connection that doesn't use it (initReplBridge skips its dead-token ladder when the override is set, :168).

**Invariant:** (1) Overrides are double-gated (specific env var AND USER_TYPE) so a leaked env var in a customer environment is inert. (2) The Override getters are the ONLY place `CLAUDE_BRIDGE_*` strings appear — grep-auditable by construction. (3) Token-undefined semantics differ per layer: access token undefined = "not logged in" (callers surface /login), base URL never undefined (always resolvable). (4) When composing an override base with server-returned URLs, prefer the OVERRIDE for derived endpoints — a staging bridge pointing at prod ingress defeats the purpose.

**Probe:** coverage caveat — no upstream unit tests. Deterministic pins: `grep -n "copy-pasted across" src/bridge/bridgeConfig.ts` (:4); `grep -n "USER_TYPE === 'ant'" src/bridge/bridgeConfig.ts` (:20,:29); `grep -n "api_base_url: baseUrl" src/bridge/remoteBridgeCore.ts` (:946); graph resolves `locoagent.src.bridge.bridgeConfig.getBridgeAccessToken` :38-40 line-exact.

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "getBridgeAccessToken getBridgeBaseUrl getBridgeTokenOverride getBridgeBaseUrlOverride", limit: 5, fields: ["signature","name","file"] });
```

## Verdict
Adopt the two-layer getter pattern wholesale whenever dev overrides exist for auth/base-URL pairs. Adapt env names; keep the single-file consolidation — its whole value is being the one grep target.
