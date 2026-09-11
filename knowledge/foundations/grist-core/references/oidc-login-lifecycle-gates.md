<!-- capsule-v2 -->
# OIDC login lifecycle — where do the config gate, protection vocabulary, and callback failure path decide whether SSO boots at all?

**Source:** grist-core Apache-2.0 `main@c057666bb93b6f93a69b0884ce023676c3a2804b`; Codebase Memory `grist-core`. **Question:** What are the exact boot-time validation gates of the OIDC login system, how is the PKCE/STATE/NONCE vocabulary composed, and what must happen to session state when a callback fails?

## Issuer flag missing ⇒ NotConfiguredError (not a crash); UNPROTECTED is a deliberate single token; failed logins delete session state BEFORE responding
**Path/Symbol:** `app/server/lib/OIDCConfig.ts` — `readOIDCConfigFromSettings()` (:152–235), `buildEnabledProtections()` (:237–257), `OIDCBuilder.initOIDC()` (:285–307), `handleCallback()` (:313–379), `getLogoutRedirectUrl()` (:396–412); `app/server/lib/oidc/Protections.ts` whole-file.
**Signature:** `readOIDCConfigFromSettings(settings: AppSettings): OIDCConfig`; `OIDCBuilder.build(sendAppPage, config?): Promise<OIDCBuilder>`; `handleCallback(sessions, req, res): Promise<void>`.
**Data Shape:** Config keys ride `settings.section("login").section("system").section(OIDC_PROVIDER_KEY)` flags; `enabledProtections: Set<"STATE"|"NONCE"|"PKCE">` default `{PKCE,STATE}` from comma-split env; `extraMetadata` JSON.parse'd with `"{}"` fallback (:211–213).

### Decisive source
```ts
// OIDCConfig.ts:156-162 — the only difference between "not configured" and "misconfigured"
let issuerUrl = "";
try {
  issuerUrl = section.flag("issuer").requireString({ envVar: "GRIST_OIDC_IDP_ISSUER" });
} catch (e) {
  throw new NotConfiguredError((e as Error).message);
}
```
```ts
// OIDCConfig.ts:360-377 — failure deletes session state BEFORE sending the response
mreq.session.oidc = { idToken: tokenSet.id_token };   // success keeps ONLY idToken for logout
res.redirect(targetUrl ?? "/");
} catch (err) {
  ...
  // Delete entirely the session data when the login failed.
  delete mreq.session.oidc;
  await this._sendErrorPage(req, res, err.userFriendlyMessage, targetUrl);
}
```

**Flow:** boot = read config → `UNPROTECTED` alone (length-1 split) logs a loud warning and returns an EMPTY set :242–246; any other invalid value re-throws as `TypeError` naming `StringUnionError.actual` + allowed values → `Issuer.discover()` → client with `response_types:["code"]` + extraMetadata spread LAST (can override everything) → if IdP metadata lacks `end_session_endpoint` AND no override AND not skipped ⇒ THROW at startup :300–305. Login = `getLoginRedirectUrl` stores `targetUrl` + protection-generated `state/nonce/code_verifier` in `session.oidc`, then builds the auth URL with `forgeAuthUrlParams`. Callback = `callbackParams(req)` → "Missing OIDC information" throw if no session entry → `_client.callback(redirectUrl, params, checks)` compares wire params vs session-held checks → userinfo → `email_verified !== true` rejects unless `ignoreEmailVerified` → profile written via `operateOnScopedSession` → session REPLACED with `{idToken}` only. Logout: skip-flag returns the plain redirect; explicit `endSessionEndpoint` overrides IdP metadata; otherwise RP-initiated logout to a STABLE `/signed-out` URI on the request origin because "OIDC providers don't allow variable redirect URIs", carrying `id_token_hint`.
**Invariant:** The three-state logout decision order is load-bearing (`skipEndSessionEndpoint` → explicit endpoint → endSessionUrl) — a porter who reorders it breaks IdPs that publish a broken/unwanted end_session_endpoint. Protection checks live in the SESSION between redirect and callback; deleting `session.oidc` on failure prevents replaying stale verifiers across attempts ("prevents several login attempts"). Token logging redacts everything except `token_type/expires_in/expires_at/scope` (`formatTokenForLogs` :93–102).
**Probe:** `test/server/lib/OIDCConfig.ts` (928L: build :105, End Session Endpoint :161, HTTP timeout :205, trusted proxy :254, ENABLED_PROTECTIONS :277, getLoginRedirectUrl :334, handleCallback :446, getLogoutRedirectUrl :866). Source pins: `grep -c 'NotConfiguredError' app/server/lib/OIDCConfig.ts` = 2; `grep -n 'signed-out' app/server/lib/OIDCConfig.ts` = :406; `grep -c 'does not propose end_session_endpoint' app/server/lib/OIDCConfig.ts` = 1.

## Get live surrounding code
**Retrieve:**
```bash
codebase-memory-mcp cli search_graph '{"project":"grist-core","query":"OIDCBuilder initOIDC handleCallback end_session_endpoint protections","limit":10,"detail":"ids"}'
```

## Verdict
Adopt the NotConfiguredError-vs-TypeError split (drives admin-UI provider status), the UNPROTECTED grammar, session-replace-with-idToken contract, and stable-redirect logout ladder; adapt env-var names and i18n'd user messages; omit Keycloak-specific testing notes. Direct mocha coverage at this pin (stubbed IdP suite); runner-blocked locally — probes recorded as source-pinned assertions.
