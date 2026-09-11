<!-- capsule-v2 -->
# Bridge session services — which per-session host services does a bridge owe an agent, and how do they degrade when the agent SDK lags the protocol?

**Source:** Vercel AI SDK Apache-2.0 `main@9d9a73f1551f2243035491e9de5a2e00ebf9eb17`; Codebase Memory `ai`. **Question:** how do you gate user-declared MCP servers, deliver structured-output schemas to agents that lack metadata support, and keep stop events flowing through legacy prompt paths?

## External MCP gating + prompt meta + three-tier send ladder
**Path/Symbol:** `packages/harness-acp/src/v1/bridge/index.ts:createExternalMcpServers` (:593–626), `createOutputSchemaPromptMeta` (:738–760), `promptActiveSession` (:762–811).
**Signature:** `createExternalMcpServers({ mcpServers, initialization }) => acp.McpServer[]`; `promptActiveSession({ session, agent, prompt, meta }) => Promise<acp.PromptResponse>`.
**Data Shape:** `mcpServers: Record<string, unknown>` (user config) validated against `initialization.agentCapabilities.mcpCapabilities`.

### Decisive source
```ts
// :607–623 — fail-closed gating of user-configured servers
if (value.type === 'acp') {
  throw new HarnessBridgeCapabilityUnsupportedError({ harnessId: bridgeType,
    message: 'ACP-transport MCP servers require client-side mcp/connect handling, which this harness does not provide.' });
}
if ((value.type === 'http' && mcpCapabilities?.http !== true) ||
    (value.type === 'sse'  && mcpCapabilities?.sse  !== true)) {
  throw new HarnessBridgeCapabilityUnsupportedError({ ... });
}
// :773–776 — native path first...
if (meta == null) return session.prompt(prompt);
if (session.promptWithMeta != null) return session.promptWithMeta({ prompt, meta });
```

**Flow:** user MCP entries must be object values; `type:'acp'` is unsupported outright; http/sse REQUIRE the agent's advertised capability — all failures are capability errors, never silent drops → structured output rides prompt `_meta` ONLY for json responseFormat + `session-prompt-meta` mapping, planting the JSON schema at the mapped path inside nested objects (:750–759) → prompting is a three-tier ladder: plain `session.prompt` when no meta; `session.promptWithMeta` when the SDK grew metadata support; otherwise reach into the recovered-session update queue — `updates.clearErrors()` then a RAW `agent.request(session/prompt {_meta})` whose promise enqueues `{kind:'stop', response}` on resolve and rejects the queue on error (:791–809) — so streamed-update consumers receive their terminal stop event even on SDKs that cannot carry prompt metadata; missing BOTH shapes throws loudly (:786–790).

**Invariant:** capability negotiation is fail-closed with named errors (`authenticate` :644–661 asserts the method was advertised before requesting it; `resolveClientApp`/`resolveGatewayValues` :663–690 fail fast when env didn't arrive); catalog refresh + permission-mode configuration happen inside ensureSession and dispose the created session on failure (:560–584). The permission request handler installed on the client answers through the active controller or cancelled — never unhandled (:420–428).

**Probe:** `packages/harness-acp/src/v1/bridge/stream-translator.test.ts` covers translation; for this seam the decisive pins live in the adapter suite read whole-file in pass 20–21 and re-read here at ranges: `packages/harness-acp/src/acp-harness.test.ts` (:482–645 env/config assertions incl. `spawns[0].env[ACP_BRIDGE_CONFIGURATION_ENV]` parse :598–611) plus `packages/harness-acp/src/v1/bridge/host-tool-mcp-server.test.ts :116–159` (listChanged announcements consumed by the same session wiring).

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "host tool relay catalog revision long poll invocation bearer token", limit: 10 });
```
Live @pin: the same BM25 page ranks `createExternalMcpServers :593-626`, `createOutputSchemaPromptMeta :738-760`, `promptActiveSession :762-811`, `resolveGatewayValues :672-690` — one page covering the whole lower half.

## Verdict
Adopt: capability-gated external servers with typed unsupported errors, schema-at-mapped-path prompt meta, and the three-tier prompt ladder that synthesizes stop events for legacy SDKs. Adapt the queue-injection shape (`{kind:'stop', response}`) to your update transport. Omit ACP method constants. Coverage caveat: runner block stands (no node_modules → vitest unrunnable); behavior pinned indirectly through adapter-level tests (no dedicated wireTurn/promptActiveSession unit file) — recorded as standing coverage caveat.
