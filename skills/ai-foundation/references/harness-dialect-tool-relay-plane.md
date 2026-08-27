<!-- capsule-v2 -->
# Dialect tool-relay plane — how do you gate a model-readable loopback endpoint to host tools without any credential?

**Source:** Vercel AI SDK Apache-2.0 `main@9d9a73f1551f2243035491e9de5a2e00ebf9eb17`; Codebase Memory `ai`. **Question:** When the helper process that calls host tools lives where the model can read its file (session dir / bundled MCP shim), how does the in-sandbox relay authorize exactly the calls the runtime actually made — and nothing else — with no bearer token to leak?

## Exact-match pre-authorization with TTL + canonical-JSON keys
**Path/Symbol:** `packages/harness-opencode/src/bridge/tool-relay-auth.ts` — `ToolRelayAuthorizer` (:6–99), `toolRelayCallKey` (:103–105), `canonicalJson` (:107–124); near-identical twin `packages/harness-codex/src/bridge/tool-relay-auth.ts` (diff: codex adds only `ToolRelayResult` type + `ToolRelayPendingCalls` class :108–133); relays `packages/harness-opencode/src/bridge/tool-relay.ts:startAuthorizedToolRelay` (:10–107) and codex twin (:14–119).
**Signature:** `startAuthorizedToolRelay({tools, emit, requestToolResult, authorizer?}): Promise<{port, close(), authorizeToolCall(call)}>`; `ToolRelayAuthorizer({ttlMs=10_000, now=Date.now})`.
**Data Shape:** authorization key = `toolName\0canonicalJson(input ?? {})` where canonicalJson recursively sorts object keys and drops undefined values; two lists — minted authorizations (TTL-expired, lazily pruned on every operation) and pending HTTP requests (FIFO per key, each with its own TTL timeout); HTTP surface = 127.0.0.1 ephemeral port, POST `/` only (else 401), unknown toolName ⇒ 403, unauthorized after TTL wait ⇒ 401, handler error ⇒ 500.

### Decisive source
```ts
// tool-relay-auth.ts (both dialects) — an authorization is consumed EXACTLY
// once; a request that arrives BEFORE its runtime event parks FIFO and is
// resolved by the later matching authorization
const pendingRequestIndex = this.pendingRequests.findIndex(
  request => request.key === key,
);
if (pendingRequestIndex !== -1) {
  const [pendingRequest] = this.pendingRequests.splice(pendingRequestIndex, 1);
  clearTimeout(pendingRequest.timeout);
  pendingRequest.resolve(true);
  return;
}
this.authorizations.push({ key, expiresAt: this.now() + this.ttlMs });
// codex tool-relay-auth.ts:108–133 — duplicate IN-FLIGHT calls coalesce onto
// one promise; deletion guarded by identity so a replaced entry survives
const existing = this.calls.get(key);
if (existing) return { result: existing, isNew: false };
const result = run();
this.calls.set(key, result);
void result.finally(() => {
  if (this.calls.get(key) === result) { this.calls.delete(key); }
}).catch(() => {});
```

**Flow:** bridge starts the relay when the start frame carries tools → the runtime's helper (codex CLI shim / opencode local MCP server `harness-tools`) POSTs `{requestId, toolName, input}` → the relay checks method/url, tool-name membership, then `waitForToolCallAuthorization`: an already-minted exact-match authorization resolves immediately (consumed), else the request parks until either the matching authorization lands or the TTL expires → on success the relay emits `tool-call` to the host, awaits `requestToolResult(requestId)`, emits `tool-result`, and answers the helper with `{result}` → `close()` rejects every parked request false and stops the server at turn end.
**Invariant:** no request can execute a host tool unless the bridge itself observed the runtime announce that EXACT (toolName, canonical-input) call within the TTL window — the endpoint holds no secret because none is needed; identical concurrent calls from one logical invocation share one host execution (codex coalescing); `close()` can never leave a helper hanging.

## Divergent authorization triggers per dialect
**Path/Symbol:** `packages/harness-codex/src/bridge/index.ts` — event-parse trigger (:235–253, see harness-codex-bridge-cli-relay-shim.md); `packages/harness-opencode/src/bridge/index.ts` — `ensureRuntime` relay start (:176–181), `buildOpenCodeConfig` local-MCP wiring (:254–271), `authorizeHostToolCall` (:1161–1174) with per-callID dedupe via `state.hostToolCallsAuthorized`.
**Signature:** opencode MCP entry: `mcp['harness-tools'] = {type:'local', command:['node', '<bootstrapDir>/host-tool-mcp.mjs'], environment:{TOOL_SCHEMAS, TOOL_RELAY_URL}}`.
**Data Shape:** codex mints authorizations by PARSING the `command_execution` event text; opencode mints them by OBSERVING the server's own tool-call announcement (name matched through `getHostToolName` incl. the `harness-tools_` prefix strip), deduped per callID so a re-observed announcement cannot double-authorize.

### Decisive source
```ts
// opencode index.ts:1161–1174 — announcement-driven authorization, deduped
function authorizeHostToolCall({ callID, toolName, input, state }): void {
  if (state.hostToolCallsAuthorized.has(callID)) return;
  state.hostToolCallsAuthorized.add(callID);
  runtime.relay?.authorizeToolCall({ toolName, input });
}
```

**Flow:** same kernel, two observation points — whichever event the dialect's runtime reliably emits for "the model asked for this call" becomes the authorization mint site; the HTTP request is always the SECOND party to arrive (or parks FIFO if it wins the race).
**Invariant:** authorization is minted ONLY from a runtime-observed call, never from the HTTP request itself — a malicious project script that discovers the loopback port but has not been announced by the runtime gets a TTL-wait then 401, and `emit`/`requestToolResult` are never reached (pinned by both tool-relay.test.ts "rejects a request from a process containing the … path" cases).
**Probe:** `packages/harness-codex/src/bridge/tool-relay-auth.test.ts` (208L, 11 cases): reject-without-auth; consume-exactly-once (second wait ⇒ false); request-before-event resolves true; FIFO of identical pendings (first true, second false after close); cross-call non-substitution (Austin auth never satisfies Paris wait); property-order canonicalization; stale-authorization expiry; close-rejects-pendings; plus ToolRelayPendingCalls coalescing (duplicate joins first promise, runCount stays 1) and post-settle restart. `packages/harness-opencode/src/bridge/tool-relay-auth.test.ts` (129L, 8 cases) pins the same authorizer contract on the opencode twin; both `tool-relay.test.ts` (100L each) pin the live-server 401-TTL and authorized-200 paths over real 127.0.0.1 sockets.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "startAuthorizedToolRelay ToolRelayAuthorizer ToolRelayPendingCalls toolRelayCallKey", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the credential-free exact-match pre-authorization pattern whenever the calling helper is model-readable — loopback binding + canonical-key authorization minted from a runtime-observed event + short TTL replaces any token scheme; adopt the dual-list (minted/pending) shape so request-before-event races resolve correctly; adopt codex's in-flight coalescing when your helper can double-fire one logical call; adapt the observation point (event-text parse vs announcement callback) to your runtime; omit this whole plane where the helper runs as a bridge-controlled stdio child — there the pass-22 ACP bearer-token relay (randomBytes(32) + timingSafeEqual) is the stronger fit. Caveat: the opencode announcement→authorization wiring (index.ts :1161–1174) is deterministic-read-only; the relay kernel itself is fully test-pinned in both dialects.
