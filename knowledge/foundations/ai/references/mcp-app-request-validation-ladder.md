<!-- capsule-v2 -->
# MCP App request validation ladder — what can an iframe safely ask the host to do?

**Source:** Vercel AI SDK Apache-2.0 `main@9d9a73f1551f...`; Codebase Memory `ai`. **Question:** Which per-method param validators must run before host callbacks fire, and what do they forbid?

## Method-scoped assert ladder
**Path/Symbol:** `packages/react/src/mcp-apps/bridge.ts` — `assertResourceReadParams` (:69–79), `assertOpenLinkParams` (:85–102), `assertDisplayModeParams` (:107–119), dispatch `getRequestResult` (:338–409).
**Signature:** each `(params: unknown) => TypedParams`, throwing `Error` on any violation; errors become JSON-RPC `-32603` via `handleRequest`.
**Data Shape:** `ui/message` and `ui/update-model-context` are the ONLY unvalidated forwards (`handlers.sendMessage?.(request.params) ?? {}`) — optional-callback with `{}` default result.

### Decisive source
```ts
function assertResourceReadParams(params: unknown): { uri: string } {
  if (!isJSONObject(params) || typeof params.uri !== 'string')
    throw new Error('Invalid resources/read params');
  if (!params.uri.startsWith('ui://'))
    throw new Error(`resources/read is limited to ui:// resources: ${params.uri}`);
  return { uri };
}
// open-link: parse with new URL() (throw ⇒ 'Invalid ui/open-link url'),
// then scheme !== 'https:' && 'http:' && 'mailto:' ⇒ 'Disallowed ... scheme'
// display-mode: mode must be exactly 'inline' | 'fullscreen' | 'pip'
```

**Flow:** every app→host REQUEST lands in `getRequestResult`'s switch → `ui/initialize` answers locally from bridge state (no handler); `tools/call`, `resources/read`, `resources/list`, `ui/open-link`, `ui/request-display-mode` require their callback AND run the validator first → unknown method throws. Notifications take a separate path (`handleNotification`: initialized / size-changed / request-teardown / message log) that never validates params — only requests are hostile.
**Invariant:** Scheme allowlists are checked on the PARSED URL's protocol, never substring-matched on the raw string — a raw-string port admits `javascript:https://evil`. Resource reads are scoped to `ui://` so an embedded app cannot exfiltrate arbitrary server resources (file://, https://). Validators throw typed, user-visible messages because the app sees them as `-32603` data.
**Probe:** deterministic: `grep -n "startsWith('ui://')" packages/react/src/mcp-apps/bridge.ts` → `73:`; `grep -n "scheme !== 'https:' && scheme !== 'http:' && scheme !== 'mailto:'" packages/react/src/mcp-apps/bridge.ts` → `97:`; `grep -n "code: -32603" packages/react/src/mcp-apps/bridge.ts` → `330:`. Direct tests: `bridge.test.ts:268/:276` ui:// scope, `:283/:292` javascript:-rejection + https-allow, `:299` malformed params.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "MCPAppBridge handleMessage initialized", limit: 10, fields: ["signature","name","file"] });
// verified live @9d9a73f: rank#1 MCPAppBridge.handleMessage :218-238
```

## Verdict
Adopt the validate-before-callback ordering and parsed-URL scheme checks verbatim; adapt the allowed scheme set / URI prefixes to your threat surface; omit nothing — dropping the ui:// scope or raw-string scheme checks reopens read exfiltration and XSS-by-link.
