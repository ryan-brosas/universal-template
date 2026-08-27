<!-- capsule-v2 -->
# Host-tool loopback relay — how do host tools reach an untrusted sandbox agent as MCP without exposing the host?

**Source:** Vercel AI SDK Apache-2.0 `main@9d9a73f1551f2243035491e9de5a2e00ebf9eb17`; Codebase Memory `ai`. **Question:** what does a bridge owe a sandboxed runtime that must LIST and CALL host tools over stdio MCP, and which failure modes must be status-coded rather than silent?

## Relay state machine (`startHostToolRelay`)
**Path/Symbol:** `packages/harness-acp/src/v1/bridge/host-tool-relay.ts:startHostToolRelay` (:64–143) + `handleInvocation` (:254–338).
**Signature:** `({ tools, serverName }) => Promise<HostToolRelay>` with `{ url, credential, bindTurn, unbindTurn, updateCatalog, waitForCatalogRefresh, close }`.
**Data Shape:** `CatalogState { tools, fingerprint, revision, servedRevision, closed, changeWaiters, refreshWaiters }`; credential = `randomBytes(32).toString('hex')` (:80); server = `createServer` on `listen(0,'127.0.0.1')` (:479–487), url `http://127.0.0.1:<port>/invoke`.

### Decisive source
```ts
// :464–477 — length-guarded constant-time bearer check
const expectedValue = Buffer.from(`Bearer ${expected}`);
const actualValue = Buffer.from(actual ?? '');
return (
  expectedValue.length === actualValue.length &&
  timingSafeEqual(expectedValue, actualValue)
);
// :289–296 — stale revision names BOTH revisions; unknown tool 404s (:298–305)
if (body.catalogRevision !== state.revision) {
  throw new RelayRequestError({ status: 409,
    message: `Host tool ${body.toolName} was invoked from stale catalog revision ` +
      `${body.catalogRevision}; the active revision is ${state.revision}.` });
}
```

**Flow:** catalog changes fingerprint through canonical JSON (key-sorted stringify, :412–431) — unchanged fingerprint returns `{changed:false}` at the SAME revision (:121–131), every change bumps `revision` and wakes long-pollers → the MCP child long-polls `/catalog/next {afterRevision}` forever (`watchCatalog`, host-tool-mcp.ts :58–88); the poll parks on a waiter raced against a 20s UNREF'D timeout (:340–359) and close resolves waiters `{closed:true}` (:220–222) → after each ListTools the child ACKs `/catalog/seen {revision}`, advancing `servedRevision = max(...)` (:228–252) → `/invoke` requires an ACTIVE bound turn (else 409 'No ACP prompt turn is active'), validates shape (400), rejects stale revision (409) or unknown tool (404) BEFORE minting anything, then mints a 64-hex correlation token, registers the invocation, emits the tool call into the stream, awaits the host result, emits the result, and answers `{output, isError?, correlationToken}` (:307–337).

**Invariant:** failed gates never consume invocation ORDER — the order counter increments only at registration after all gates pass, so FIFO pairing downstream stays dense (pinned by relay.test.ts :241–244: exactly two registrations, last `order:2`). The relay-client keeps a `keepAlive Agent({timeout:0})` because "a host-tool call can remain pending while a person reviews an approval" (host-tool-relay-client.ts :3–7); >300,001ms of fake time leaves the request unsettled (relay-client.test.ts :52–53). The bridge writes the seed catalog to `${bridgeStateDir}/host-tools.json` mode 0o600 and passes exactly THREE env vars to the stdio MCP child (`AI_SDK_ACP_HOST_TOOLS_FILE/_RELAY_URL/_RELAY_CREDENTIAL`, all fail-fast at module load — index.ts :473–501, host-tool-mcp.ts :12–20).

**Probe:** `packages/harness-acp/src/v1/bridge/host-tool-relay.test.ts` — `:185–248` pins 409-stale/404-unknown without consuming order; `:164–178` pins the held poll's 20s setTimeout and close resolving `{closed:true}`; `host-tool-mcp-server.test.ts` runs a REAL `InMemoryTransport` client↔server pair and pins the token surfacing in result `_meta['ai-sdk-harness-acp-correlation']` (:99–111) plus `sendToolListChanged` announcements (:116–159).

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "host tool relay catalog revision long poll invocation bearer token", limit: 10 });
```
Live @pin: rank#1 `updateCatalog :121-131`, `catalogFingerprint :412-418`, `handleCatalogNext :199-226`; `refreshHostToolCatalog` (:5–33) fail-closes with HarnessBridgeCapabilityUnsupportedError when the implementation never loads the revision ("host tools cannot be exposed safely") unless the unchanged catalog is empty.

## Verdict
Adopt: loopback-only ephemeral port + randomBytes(32) length-guarded timingSafeEqual bearer; canonical-JSON fingerprints gating revision bumps; seen-ACK refresh handshake with bounded wait; status-coded invocation failures (400/401/404/409/413/500 via RelayRequestError); order-preserving registration; no-deadline HTTP client for human-gated calls; 16MiB body cap. Adapt endpoint paths, server naming, and the MCP child bootstrap to your host. Omit the ACP `McpServer` env-array shape if your transport passes config differently. Coverage caveat: runner block stands (no node_modules); integration behavior verified by direct test reads at pin.
