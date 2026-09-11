<!-- capsule-v2 -->
# MCP App bridge init gate — when may the host push notifications into an untrusted iframe?

**Source:** Vercel AI SDK Apache-2.0 `main@9d9a73f1551f...`; Codebase Memory `ai`. **Question:** How does the host-side JSON-RPC bridge avoid losing or leaking host→app notifications before the untrusted app finishes its handshake?

## Queue-until-initialized notification gate
**Path/Symbol:** `packages/react/src/mcp-apps/bridge.ts` — `MCPAppBridge` (:142), `initialized` flag (:143), `pendingNotifications` (:144), `sendNotification` (:438–447), `handleNotification` 'ui/notifications/initialized' arm (:416–420), `flushNotifications` (:452–458).
**Signature:** `sendNotification(notification: Omit<MCPAppJsonRpcNotification,'jsonrpc'>): void`; `flushNotifications(): void`.
**Data Shape:** `pendingNotifications: MCPAppJsonRpcNotification[]` (drained by swap-and-clear); `initialized` flips only on the app's `ui/notifications/initialized` notification.

### Decisive source
```ts
private sendNotification(notification) {
  const message = { jsonrpc: '2.0' as const, ...notification };
  if (!this.initialized && !notification.method.includes('sandbox')) {
    this.pendingNotifications.push(message);   // held, not dropped
    return;
  }
  this.post(message);
}
private flushNotifications(): void {
  const notifications = this.pendingNotifications;
  this.pendingNotifications = [];
  for (const notification of notifications) this.post(notification);
}
```

**Flow:** every host→app notify (`tool-input`, `tool-result`, `tool-cancelled`, `host-context-changed`) routes through `sendNotification` → pre-initialize messages are QUEUED (never dropped) → app sends `ui/notifications/initialized` → `initialized=true`, queue flushed in order, then `onInitialized` fires → only messages whose method contains `'sandbox'` (the `ui/notifications/sandbox-resource-ready` bootstrap reply) bypass the gate because the proxy needs them to even boot the app.
**Invariant:** The handshake is APP-driven: the host must not deliver queued state until the app declares readiness, but must not lose that state either — dropping pre-init tool input silently breaks apps that mount after the model streamed. The sandbox bypass is the single sanctioned exception.
**Probe:** deterministic: `grep -c pendingNotifications packages/react/src/mcp-apps/bridge.ts` → `5`; `grep -c flushNotifications packages/react/src/mcp-apps/bridge.ts` → `2`. Direct tests: `packages/react/src/mcp-apps/bridge.test.ts:65` "queues tool notifications until the app is initialized", `:23` "responds to app initialization requests".

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "sendToolInput pendingNotifications", limit: 10, fields: ["signature","name","file"] });
// verified live @9d9a73f: rank#1 MCPAppBridge.sendToolInput :254-259
```

## Verdict
Adopt the queue-until-handshake gate plus the explicit sandbox-notification bypass; adapt method names/version constant (`MCP_APP_PROTOCOL_VERSION = '2026-01-26'`, :12) to your spec; omit nothing — a fire-and-forget port loses tool input for late-mounting apps.
