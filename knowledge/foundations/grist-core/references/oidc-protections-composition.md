<!-- capsule-v2 -->
# OIDC protection composition — how do STATE/NONCE/PKCE each contribute session info, auth-URL params, and callback checks without knowing about each other?

**Source:** grist-core Apache-2.0 `main@c057666bb93b6f93a69b0884ce023676c3a2804b`; Codebase Memory `grist-core`. **Question:** How is a set of independent CSRF/replay protections composed into one login flow, and what happens when a required session field went missing mid-flow?

## Three strategy objects, three merge points, one "Login is stale" failure message
**Path/Symbol:** `app/server/lib/oidc/Protections.ts` — `EnabledProtection = StringUnion("STATE","NONCE","PKCE")` (:5–7); `PKCEProtection`/`NonceProtection`/`StateProtection` classes; `ProtectionsManager` (:89–127).
**Signature:** `interface Protection { generateSessionInfo(): SessionOIDCInfo; forgeAuthUrlParams(sessionInfo): AuthorizationParameters; getCallbackChecks(sessionInfo): OpenIDCallbackChecks }`; manager merges via `Object.assign` loops.
**Data Shape:** `SessionOIDCInfo = { state?, nonce?, code_verifier? }` persisted in `session.oidc` between redirect and callback. Construction order is FIXED: STATE, then NONCE, then PKCE (:96–105).

### Decisive source
```ts
// Protections.ts:16-21 + PKCE arms — the checkIsSet guard that turns missing session fields into "Login is stale"
function checkIsSet(value: string | undefined, message: string): string {
  if (!value) { throw new Error(message); }
  return value;
}
// PKCEProtection.getCallbackChecks -> { code_verifier: checkIsSet(sessionInfo.code_verifier, "Login is stale") }
// NonceProtection  ... "Login is stale"   | StateProtection ... "Login or logout failed to complete"
```

**Flow:** `generateSessionInfo()` assigns each enabled protection's secret into the session at login-start → `forgeAuthUrlParams()` puts the public halves (state, nonce, `code_challenge=S256(verifier)`) into the authorization URL → after redirect, `getCallbackChecks()` rebuilds the expected values FROM THE SESSION and hands them to openid-client's `callback()`, which throws on mismatch → "Login is stale" fires when the session entry vanished (expired cookie, restarted server, replayed callback) rather than a forged param.
**Invariant:** Session info is the single source of truth for ALL THREE mechanisms — nothing is stored in the URL or a server-side store keyed differently, so enabling/disabling a protection never changes storage shape (absent keys simply aren't assigned). The STATE-vs-others error-message split is deliberate: state mismatch = interrupted logout/login handshake; nonce/PKCE mismatch = stale login context.
**Probe:** `test/server/lib/OIDCConfig.ts` GRIST_OIDC_IDP_ENABLED_PROTECTIONS suite :277–333 (invalid values rejected with allowed-values message; UNPROTECTED accepted). Source pins: `grep -c 'Login is stale' app/server/lib/oidc/Protections.ts` = 3 (PKCE + NONCE + shared helper usage sites); `grep -n 'S256' app/server/lib/oidc/Protections.ts` resolves the challenge method.

## Get live surrounding code
**Retrieve:**
```bash
codebase-memory-mcp cli search_graph '{"project":"grist-core","query":"ProtectionsManager EnabledProtection codeVerifier nonce state generateSessionInfo","limit":10,"detail":"ids"}'
```

## Verdict
Adopt the strategy-object composition (each protection contributes exactly three functions; merging is Object.assign order-stable); adapt the secret generators to your crypto stack; omit openid-client-specific types while keeping the session-info→auth-params→callback-checks triple contract. Coverage caveat: no standalone unit suite drives Protections.ts at this pin — behavior pinned through the OIDCConfig ENABLED_PROTECTIONS suite plus source-pinned greps.
