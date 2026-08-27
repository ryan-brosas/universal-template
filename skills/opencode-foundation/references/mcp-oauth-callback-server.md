<!-- capsule-v2 -->
# MCP OAuth callback server — how do you run an OAuth authorization-code flow from a headless CLI without leaking half-written credentials, replaying credentials after a URL change, or letting a second instance steal your callback?

**Source:** opencode MIT `dev@03521003fafd`; Codebase Memory `opencode`. **Question:** A CLI must complete the MCP OAuth authorization-code flow (dynamic client registration, PKCE, loopback redirect) where token exchange can fail mid-way, stored credentials may belong to a different server URL, and multiple CLI instances may run on one machine sharing the default callback port.

## Pending-token provider: commit only on success
**Path/Symbol:** `packages/opencode/src/mcp/oauth-provider.ts` (`McpOAuthProvider` :26-181, `McpOAuthPendingProvider` :183-238, `commit` :212-236) + `packages/opencode/src/mcp/index.ts` (`startAuth` :806-870, `authenticate` :872-916, `finishAuth` :918-942).
**Signature:** `startAuth(mcpName) → Effect<{authorizationUrl, oauthState}, NotFoundError>`; `finishAuth(mcpName, authorizationCode) → Effect<Status, NotFoundError>`.
**Data Shape:** oauthState = 64 hex chars from crypto.getRandomValues(32 bytes); `pendingOAuthTransports: Map<name, {transport, provider?}>` module-level (index.ts :111).

### Decisive source
```ts
// oauth-provider.ts:183-210 — the explicit-flow provider keeps tokens in MEMORY
export class McpOAuthPendingProvider extends McpOAuthProvider {
  private pendingClientInfo?: OAuthClientInformationFull
  private pendingTokens?: OAuthTokens
  override async saveTokens(tokens: OAuthTokens): Promise<void> { this.pendingTokens = tokens }
  ...
  async commit(): Promise<void> {
    if (!this.pendingTokens) return
    await Effect.runPromise(this.auth.set(this.mcpName, {
      tokens: { accessToken: ..., refreshToken: ..., expiresAt: ..., scope: ... },
      clientInfo: this.pendingClientInfo && !this.config.clientId ? { clientId: ..., clientSecret: ..., ... } : undefined,
    }, this.serverUrl))
  }
}
// index.ts:855-868 — the EXPECTED failure mode carries the redirect URL
return yield* Effect.tryPromise({
  try: () => { const client = createClient(directory); return client.connect(transport).then(async () => { await authProvider.commit(); return { authorizationUrl: "", oauthState, client } }) },
}).pipe(Effect.catch((error) => {
  if (error instanceof UnauthorizedError && capturedUrl) {
    pendingOAuthTransports.set(mcpName, { transport, provider: authProvider })
    return Effect.succeed({ authorizationUrl: capturedUrl.toString(), oauthState })
  }
  return Effect.die(error)
}))
// index.ts:905-910 — CSRF double-check before finishing
const storedState = yield* auth.getOAuthState(mcpName)
if (storedState !== result.oauthState) {
  yield* auth.clearOAuthState(mcpName)
  throw new Error("OAuth state mismatch - potential CSRF attack")
}
```

**Flow:** startAuth ensures the callback server runs (custom port/path from an effective redirectUri), generates + persists oauthState via auth.updateOAuthState, builds a PendingProvider whose onRedirect captures the authorization URL, and attempts a StreamableHTTP connect. If stored/refreshed tokens are already valid the connect SUCCEEDS: any SDK refresh landed in memory and commit() persists it, authorizationUrl comes back "" and authenticate() short-circuits straight to storeClient. If UnauthorizedError fires with a captured URL, the transport+provider go into pendingOAuthTransports and the URL is returned for browser opening. authenticate(): waitForCallback(oauthState, mcpName) promise, invoke the onAuthorization callback, open the browser (failure publishes BrowserOpenFailed — an event, not an error), await the code, then verify the STORED oauthState still equals the issued one (mismatch → clear + throw "potential CSRF attack"), clear state, finishAuth. finishAuth: look up the pending entry (missing → throw "No pending OAuth flow"), call transport.finishAuth(code) (the SDK exchanges the code; saveTokens lands in memory), on success commit() → clearCodeVerifier → delete the pending entry → createAndStore(enabled:true). On exchange failure it returns a failed status and the pending entry REMAINS — the flow is retryable, and no partial credentials were ever written.

**Invariant:** Credentials reach durable storage exactly once, only after the full code exchange succeeds (commit() is the single write point; no pendingTokens → no write). A mismatch between issued and stored state aborts as a potential CSRF attack. A failed exchange leaves the pending flow intact for retry.
**Probe:** `packages/opencode/test/server/httpapi-mcp-oauth.test.ts` ("preserves oauth state when starting OAuth" pins POST /mcp/demo/auth returning the handler's exact `{authorizationUrl, oauthState}` pair — the HTTP layer must not transform the state); httpapi-mcp.test.ts pins the 400 unsupported-OAuth body `{"error":"MCP server demo does not support OAuth"}` for local servers. Source pin:
```bash
grep -n 'pendingTokens' packages/opencode/src/mcp/oauth-provider.ts        # expect 9
grep -n 'CALLBACK_TIMEOUT_MS' packages/opencode/src/mcp/oauth-callback.ts   # expect 2
```

## URL-scoped credential store
**Path/Symbol:** `packages/opencode/src/mcp/auth.ts` (filepath/lockKey :37-38, read :65-71, mutate :76-82, getForUrl :89-96, updateField/clearField :112-131) + `oauth-provider.ts` (clientInformation :56-79, tokens :96-110, state :147-163).
**Signature:** `getForUrl(mcpName, serverUrl) → Effect<Entry|undefined>`; Entry = `{tokens?, clientInfo?, codeVerifier?, oauthState?, serverUrl?}`.
**Data Shape:** JSON file at Global.Path.data/mcp-auth.json written 0o600; every read/write under an EffectFlock lock keyed by the file path; malformed content decodes to {}.

### Decisive source
```ts
// auth.ts:89-96 — credentials are scoped to the server URL they were obtained for
const getForUrl = Effect.fn("McpAuth.getForUrl")(function* (mcpName, serverUrl) {
  const entry = yield* get(mcpName)
  if (!entry) return undefined
  if (!entry.serverUrl) return undefined
  if (entry.serverUrl !== serverUrl) return undefined
  return entry
})
// oauth-provider.ts:68-70 — expired dynamic-registration secrets force re-registration
if (entry.clientInfo.clientSecretExpiresAt && entry.clientInfo.clientSecretExpiresAt < Date.now() / 1000) {
  return undefined
}
// oauth-provider.ts:147-163 — state() is a GENERATOR: the SDK calls it during automatic auth
async state(): Promise<string> {
  const entry = await Effect.runPromise(this.auth.get(this.mcpName))
  if (entry?.oauthState) { return entry.oauthState }
  const newState = Array.from(crypto.getRandomValues(new Uint8Array(32))).map((b) => b.toString(16).padStart(2, "0")).join("")
  await Effect.runPromise(this.auth.updateOAuthState(this.mcpName, newState))
  return newState
}
```

**Flow:** All token/client-info reads go through getForUrl — a stored entry whose serverUrl differs from the current URL is invisible, so a URL change forces fresh auth instead of replaying old credentials. Dynamic client registration results store clientSecretExpiresAt; an expired secret reads as absent, triggering re-registration. state() must GENERATE when absent because the SDK invokes it during automatic auth on first connect, before any explicit startAuth pre-saved a value (the comment pins this). invalidateCredentials does field-level surgery: "all" removes the entry, "client"/"tokens" delete just that field.

**Invariant:** A credential is only ever presented to the exact server URL it was obtained for. The auth file is 0o600 and cross-process locked; corrupt content degrades to empty rather than crashing.
**Probe:** Source pin:
```bash
grep -n '0o600' packages/opencode/src/mcp/auth.ts                          # expect 1
grep -n 'flock.withLock(lockKey)' packages/opencode/src/mcp/auth.ts        # expect 2
grep -n 'clientSecretExpiresAt' packages/opencode/src/mcp/oauth-provider.ts # expect 3
```

## State-keyed loopback callback server
**Path/Symbol:** `packages/opencode/src/mcp/oauth-callback.ts` (module state :9-24, handleRequest :42-103, ensureRunning :105-131, waitForCallback :133-147, cancelPending :149-161, isPortInUse :163-172).
**Signature:** `ensureRunning(redirectUri?) → Promise<void>`; `waitForCallback(oauthState, mcpName?) → Promise<string>` (resolves with the code).
**Data Shape:** `pendingAuths: Map<state, {resolve, reject, timeout}>`; reverse index `mcpNameToState: Map<name, state>`; default 127.0.0.1:19876 path /mcp/oauth/callback; CALLBACK_TIMEOUT_MS = 5 minutes (:24).

### Decisive source
```ts
// oauth-callback.ts:110-121 — another instance owns the port: silently defer
if (server && (currentPort !== port || currentPath !== path)) { await stop() }
if (server) return
const running = await isPortInUse(port)   // raw TCP connect probe
if (running) { return }
// oauth-callback.ts:56-90 — state enforcement ladder
if (!state) { res.writeHead(400, ...); res.end(OauthCallbackPage.error("Missing required state parameter - potential CSRF attack", ...)); return }
if (error) { /* reject pending with the description */ res.writeHead(200, ...error page...); stopIfIdle(); return }
if (!pendingAuths.has(state)) { res.writeHead(400, ...); res.end(... "Invalid or expired state parameter - potential CSRF attack" ...); return }
const pending = pendingAuths.get(state)!
clearTimeout(pending.timeout); pendingAuths.delete(state); cleanupStateIndex(state)
pending.resolve(code)
res.writeHead(200, ...); res.end(OauthCallbackPage.success({ provider: "MCP" }))
stopIfIdle()
```

**Flow:** ensureRunning parses port/path from the effective redirect URI (parseRedirectUri: unparseable → defaults), stops a server bound to a different port/path, and defers silently when the port is already in use (another opencode instance owns the callback; this instance's waitForCallback will time out, which is the honest outcome). waitForCallback registers a 5-minute timeout keyed by STATE (not name) that rejects "authorization took too long"; the reverse index lets cancelPending(name) find and reject the right entry ("Authorization cancelled"). Request handling: missing state → 400 CSRF page; provider error param → reject the pending promise with the description AND respond 200 with an error page (the user's browser shows the reason); unknown/expired state → 400; valid → resolve(code), success page, stopIfIdle(). stopIfIdle closes the listener whenever pendingAuths empties — the port is held only while a flow is live. removeAuth = cancelPending + pendingOAuthTransports.delete.

**Invariant:** The callback resolves exactly once per state (delete-before-resolve); the listener exists only while at least one flow is pending; a foreign process on the callback port is detected by probe, never fought; every non-success response path names the CSRF risk explicitly.
**Probe:** Source pin:
```bash
grep -n 'mcpNameToState' packages/opencode/src/mcp/oauth-callback.ts  # expect 8
grep -n 'stopIfIdle()' packages/opencode/src/mcp/oauth-callback.ts     # expect 5
```

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "opencode", query: "McpOAuthPendingProvider commit getForUrl waitForCallback pendingAuths mcpNameToState", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt commit-on-success memory-pending credential staging for any multi-step auth flow: a single write point after the final exchange succeeds, so failed exchanges leave the flow retryable and never half-persisted. Adopt URL-scoped credential lookup — binding stored credentials to the exact origin they were obtained for is the cheapest defense against credential replay after config drift. Adopt state-keyed (not name-keyed) callback resolution with a name→state reverse index for cancellation, a bounded wait timeout, and idle-shutdown of the loopback listener. Adopt the silent-defer-on-port-in-use TCP probe for multi-instance CLIs. Adapt the 127.0.0.1:19876 default and HTML pages to your host; omit the BrowserOpenFailed event publication (use your own channel). Direct tests read whole (httpapi-mcp-oauth.test.ts 73L, httpapi-mcp.test.ts 223L); bun runner blocked at this checkout (no node_modules), probes are byte-exact greps.
