<!-- capsule-v2 -->
# MCP OAuth token plane — how do SSE servers get bearer tokens without blocking connect, and how does the auth callback loop back into a reconnect?

**Source:** continue Apache-2.0 `main@5522c6f44ca0ac3528b37244818fbfa39b5af470`; Codebase Memory `continue`. **Question:** How does a porter attach OAuth credentials to long-lived MCP connections with zero in-memory state and no circular imports?

## Disk-backed per-URL token store + sse-only attach at connect time + state-mapped localhost callback that refreshes the exact connection

**Path/Symbol:** `core/context/mcp/MCPOauth.ts` whole (349 lines): `getOauthToken` (:233–237), `performAuth` (:243–271), `handleMCPOauthCode` (:276–344), `MCPConnectionOauthProvider` (:70–231, storage :136–162, clientMetadata :119–134, redirectToAuthorization :207–230); consumer `core/context/mcp/MCPConnection.connectClient:151–169`; removal via `removeMCPAuth` (:346–349).
**Signature:** `getOauthToken(mcpServerUrl: string, ide: IDE): Promise<string | undefined>`; provider implements MCP SDK `OAuthClientProvider`.
**Data Shape:** GlobalContext `mcpOauthStorage[serverUrl] = {clientInformation?, tokens?, codeVerifier?}` — every read is zod `parseAsync`, every write a whole-file RMW (stateless disk store capsule); module-level `authenticatingContexts: Map<url, ctx>` + `stateToServerUrl: Map<state, url>`; ONE singleton localhost:3000 `http.Server`.

### Decisive source
```ts
// consumer side — sse transports only:
if (this.options.type === "sse") {           // "currently support oauth for sse transports only"
  const accessToken = await getOauthToken(this.options.url, this.extras?.ide!);
  if (accessToken) {
    this.isProtectedResource = true;
    this.options.requestOptions.headers = {...this.options.requestOptions.headers,
      Authorization: `Bearer ${accessToken}`};   // mutated IN PLACE before transport build
  }
}
// callback side — close server BEFORE exchanging the code:
if (serverInstance) await new Promise(res => serverInstance!.close(() => { serverInstance = null; res(); }));
const authStatus = await auth(authProvider, { serverUrl, authorizationCode });
if (authStatus === "AUTHORIZED") {
  const { MCPManagerSingleton } = await import("./MCPManagerSingleton"); // avoid cyclic imports
  await MCPManagerSingleton.getInstance().refreshConnection(serverId);
}
```

**Flow:** `getOauthToken` is deliberately FAIL-OPEN — fresh provider, read stored tokens, return `access_token` or undefined; it never triggers an auth flow, so connecting to an unauthenticated-yet server proceeds anonymously. `performAuth` generates a uuid `state`, registers both maps, and delegates to the SDK's `auth()`; `clientMetadata` embeds state INTO redirect_uris so dynamic registration carries it. `redirectToAuthorization` starts the singleton localhost:3000 listener ONLY when the IDE has no `getExternalUri` or the redirect still contains "localhost" (web VS Code redirects through its own mechanism). The callback handler resolves the target server by `state` (fallback: single-context heuristic when state is missing), closes the local server BEFORE exchanging the code (frees the port for a subsequent flow), and on AUTHORIZED dynamically imports the manager to force-refresh exactly that connection — closing the loop into config reload (reconcile capsule). Errors toast through the IDE; `finally` always cleans both maps. `codeVerifier()` returns `""` (not undefined) when absent.
**Invariant:** token reads are non-blocking and anonymous-tolerant; header mutation happens on the connection's OWN options object BEFORE transport construction, which is invisible to the manager's url-only remote equality (deliberate); exactly one localhost OAuth listener exists process-wide.
**Probe:** `core/context/mcp/MCPOauth.vitest.ts` (whole 300L): undefined when nothing stored (:53–56), access_token round-trip (:58–71), per-URL independence (:73–97), performAuth delegates with `{serverUrl}` (:101–119), removeMCPAuth clears only its server and tolerates absence (:122–181), getExternalUri consulted with localhost:3000 / absent-fallback / rejection-tolerant (:184–237), concurrent flows (:241–255), failure cleanup (:259–287). Trace evidence this pass: inbound `getOauthToken` callers_total 2 = {connectClient, vitest}.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "continue", query: "oauth token provider authorization code verifier redirect localhost callback protected resource", limit: 12 });
```

## Verdict
Adopt the fail-open token read, disk-backed per-server storage, and state-mapped callback with close-before-exchange; adapt the trigger point (attach-at-connect vs attach-per-request) to your transport; omit the external-URI branch if you have no browser-hosted IDE. Trap: because remote reconcile compares urls only, rotating a token must mutate the SAME options object (or force-refresh) — writing a fresh options struct would look like an unrelated change and silently skip reconnect.
