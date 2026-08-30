<!-- capsule-v2 -->
# MCP App tool allowlist — how does an untrusted iframe get scoped access to host tools?

**Source:** Vercel AI SDK Apache-2.0 `main@9d9a73f1551f...`; Codebase Memory `ai`. **Question:** When the app issues `tools/call`, what separates "tool exists on the host" from "tool this app may invoke"?

## Deny-by-default app-visible tool gate
**Path/Symbol:** `packages/react/src/mcp-apps/bridge.ts` — `getRequestResult` 'tools/call' arm (:356–371); handler contract `MCPAppBridgeHandlers.allowedTools` in `types.ts:31–35`; capability advertising at `ui/initialize` (:342–354).
**Signature:** `case 'tools/call': assertToolCallParams(request.params) → allowedTools.includes(params.name) → handlers.callTool(params)`.
**Data Shape:** `assertToolCallParams` (:55–64) requires JSON-object params with string `name`, normalizes `arguments` to undefined unless a JSON object.

### Decisive source
```ts
case 'tools/call': {
  if (this.handlers.callTool == null)
    throw new Error('No tools/call handler configured');
  const params = assertToolCallParams(request.params);
  // Deny-by-default: ... Omitting `allowedTools` exposes no
  // tools, rather than forwarding every requested tool to `callTool`.
  if (this.handlers.allowedTools == null ||
      !this.handlers.allowedTools.includes(params.name)) {
    throw new Error(`Tool is not app-visible: ${params.name}`);
  }
  return this.handlers.callTool(params);
}
```

**Flow:** app request → params validated → TWO independent gates: (1) no `callTool` callback ⇒ hard error, (2) name not in `allowedTools` (or allowlist omitted) ⇒ "Tool is not app-visible" → only then does the untrusted frame reach the host's real MCP client. At handshake, `hostCapabilities.serverTools: {}` is advertised IFF `callTool` is configured, so the app learns capability presence without learning the list.
**Invariant:** An absent allowlist means ZERO visible tools — not "everything". A porter who treats `allowedTools?: string[]` as optional-filter instead of optional-gate turns every UI-embedded app into a full-tool-execution oracle. Errors surface as JSON-RPC `-32603` with the message (`handleRequest`, :320–333), and unknown methods throw `Unsupported MCP App method`.
**Probe:** deterministic: `grep -n "Tool is not app-visible" packages/react/src/mcp-apps/bridge.ts` → `368:`; `grep -n "handlers.allowedTools == null" packages/react/src/mcp-apps/bridge.ts` → `365:`; `grep -nF 'Unsupported MCP App method' packages/react/src/mcp-apps/bridge.ts` → `407:`. Direct tests: `bridge.test.ts:143` denies when `allowedTools` omitted, `:176` denies non-listed names, `:97` proxies listed ones.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "acceptsEvent targetOrigin", limit: 10, fields: ["signature","name","file"] });
// verified live @9d9a73f: rank#1 MCPAppBridge.acceptsEvent :208-213 (same class, request funnel)
```

## Verdict
Adopt deny-by-default allowlisting and the two-gate ordering (handler-configured check BEFORE visibility check); adapt the error taxonomy to your RPC envelope; omit nothing — filtering-instead-of-gating is the classic wrong port.
