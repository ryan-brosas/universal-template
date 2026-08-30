<!-- capsule-v2 -->
# MCP connect state machine — how does one server connection go from not-connected to connected without hanging, duplicating, or resurrecting stale capabilities?

**Source:** continue Apache-2.0 `main@5522c6f44ca0ac3528b37244818fbfa39b5af470`; Codebase Memory `continue`. **Question:** How does a porter implement a single-server connect lifecycle that survives forced refreshes, aborts, timeouts, and half-working servers?

## not-connected → connecting → connected | error, with cleared capability lists, a three-way abort race, and capability-gated fail-soft enumeration

**Path/Symbol:** `core/context/mcp/MCPConnection.ts` whole (625 lines): `connectClient` (:122–413), `constructStdioTransport` (:556–613), `resolveCommandForPlatform` (:423–447), `resolveCwd`/`resolveWorkspaceCwd` (:454–492), `disconnect` (:101–106).
**Signature:** `connectClient(forceRefresh: boolean, externalSignal: AbortSignal): Promise<void>`; status field ∈ `"not-connected" | "connecting" | "connected" | "error" | "disabled"`.
**Data Shape:** per-connection: SDK `Client`, own `AbortController`, `connectionPromise: Promise | null` (single-flight slot), capability arrays (tools/prompts/resources/resourceTemplates) + errors[]/infos[]/stdioOutput.

### Decisive source
```ts
if (!forceRefresh) {
  if (this.status === "connected") return;        // idempotent no-op
  if (this.connectionPromise) { await this.connectionPromise; return; } // single-flight
}
this.status = "connecting";
this.tools = []; this.prompts = []; /* ...all capability lists + errors cleared */
this.abortController.abort(); this.abortController = new AbortController();
this.connectionPromise = Promise.race([
  externalAbortListener,   // manager generation swap
  ownAbortListener,        // disconnect()/re-connect
  (async () => {
    const timeoutController = new AbortController();
    const connectionTimeout = setTimeout(() => timeoutController.abort(),
      this.options.timeout ?? DEFAULT_MCP_TIMEOUT /* 20_000 */);
    await Promise.race([timeoutRejection, connectAndEnumerate()]);
  })(),
]);
```

**Flow:** `disabled` short-circuits everything. Connect start clears ALL capability lists and captured stdio output — stale tools never survive a reconnect. Transport selection: `command` present ⇒ stdio REGARDLESS of type; explicit sse / streamable-http / websocket honored; unknown type ⇒ throw (test-pinned); NO type ⇒ try streamable-http then fall back to SSE, combined error if both fail. Stdio recovery: error starting with "StdioClientTransport already started" ⇒ close client and reconnect once. After connect, enumeration is capability-GATED (`getServerCapabilities()`) and each `listX` failure is fail-soft into `errors[]` while status still becomes `connected` — a server that advertises but fails tools still connects with empty lists. Error enrichment: spawn+ENOENT ⇒ ``install the <cmd> CLI`` plus uv/npx doc links in infos[]; 401/Unauthorized ⇒ `isProtectedResource = true`; captured stdout/stderr appended to the message; parse of `${{ secrets.* }}` happens BEFORE connecting and pushes hub-guidance errors. Platform quirks: Windows batch commands (npx/uv/uvx/pnpx/dlx/nx/bunx) wrapped via `cmd.exe /c` UNLESS a win32 host drives a WSL remote; cwd resolution falls back to homedir() when the resolved workspace URI contains "://" (remote URIs can't be spawn cwd).
**Invariant:** exactly one connection attempt per connection object at a time (single-flight slot nulled in `finally`); forced refresh bypasses both the idempotence check AND the in-flight await — the old attempt is killed by the abortController swap, not awaited; status ends at exactly one terminal value per attempt.
**Probe:** `core/context/mcp/MCPConnection.vitest.ts` (whole 460L — direct suite for this class): invalid type rejected inside connectClient with `errors[0]` containing "Unsupported transport type: invalid" (:103–119); already-connected short-circuit proves no reconnect (:286–297); timeout ⇒ error "Failed to connect" (:268–284); ENOENT ⇒ `'command "test-cmd" not found'` enrichment (:299–311); resolveCwd homedir fallback for `vscode-remote://` URIs (:179–188); all four resolveCommandForPlatform wrap/no-wrap branches incl. WSL exemption (:364–459). The suite also mocks `../../util/shellPath` (:12–16), pinning the PATH seam boundary.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "continue", query: "MCP connection connectClient status transport stdio sse streamable http fallback timeout", limit: 12 });
```
(Graph caveat recorded this pass: inbound trace on `connectClient` returns `callers_total: 0` — it is invoked through the manager's dynamic dispatch.)

## Verdict
Adopt the state machine shape: cleared-on-connect capability lists, per-connection single-flight with forced bypass, three-way abort race with a work-internal timeout controller, and capability-gated fail-soft enumeration; adapt transport detection to your protocol set; omit the Windows/WSL command wrapping if your host is POSIX-only. Trap: `disconnect()` closes client AND transport and flips status to `disabled` when asked — re-enabling must reset status to `not-connected` before reconnecting or the disabled guard eats the attempt.
