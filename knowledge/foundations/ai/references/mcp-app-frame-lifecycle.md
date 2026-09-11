<!-- capsule-v2 -->
# MCP App frame lifecycle — how does the React host wire, bootstrap, and tear down the sandbox proxy?

**Source:** Vercel AI SDK Apache-2.0 `main@9d9a73f1551f...`; Codebase Memory `ai`. **Question:** How does `MCPAppFrame` keep bridge identity, origin checks, and tool-state replay correct across React effect re-runs?

## Proxy-ready handshake with ref-mirrored state
**Path/Symbol:** `packages/react/src/mcp-apps/app-frame.tsx` — `deriveTargetOrigin` (:19–26), mount effect (:95–152), `sandbox-proxy-ready` intercept (:119–130), cleanup (:137–143), refs (:60–68), follow-up effects (:154–174).
**Signature:** `deriveTargetOrigin(url: string): string` — concrete origin from `new URL(url, location.href).origin`, malformed URL ⇒ host origin, never `'*'`.
**Data Shape:** refs mirror props (`inputRef`, `outputRef`, `hostContextRef`, `initializedRef`, `bridgeRef`) so the message listener closes over CURRENT values without re-binding the window listener.

### Decisive source
```ts
const onMessage = (event: MessageEvent) => {
  if (!bridge.acceptsEvent(event)) return;      // source window + origin
  if (event.data?.jsonrpc === '2.0' &&
      event.data.method === 'ui/notifications/sandbox-proxy-ready') {
    bridge.sendSandboxResourceReady({           // proxy asked: NOW send app HTML
      html: resource.html,
      csp: resourceCSP,                         // sanitized policy string
      sandbox: innerSandbox,                    // 'allow-scripts allow-forms'
      allow: resourceAllow,                     // permission intersection
    });
    return;
  }
  bridge.handleMessage(event);
};
...
return () => {
  initializedRef.current = false;
  window.removeEventListener('message', onMessage);
  void bridge.teardownResource().catch(() => {}); // graceful app teardown FIRST
  bridge.close();                                  // reject pendings + clear queue
  bridgeRef.current = undefined;
};
```

**Flow:** mount → fresh `MCPAppBridge` per effect run (deps: hostInfo, innerSandbox, resource.html, allow, CSP, sandboxUrl, targetOrigin) → proxy announces readiness → host replies `sandbox-resource-ready` carrying html+csp+sandbox+allow → app initializes (init gate flushes queued notifications; `onInitialized` wrapper replays CURRENT input/output via refs) → subsequent input/output prop changes push through effects guarded by `initializedRef.current && x !== undefined` → unmount/re-run tears down gracefully then closes.
**Invariant:** Every inbound frame is checked against BOTH the exact source window (`event.source === targetWindow`) and the expected origin before any handler runs. `targetOrigin` for OUTBOUND posts is derived to a CONCRETE origin (never `'*'`; `'null'` fallback keeps opaque-origin iframes working). Teardown order is request-then-close so the app can clean up before its channel dies. Replaying input/output at init (not only on change) is what makes late-initializing apps see streamed state.
**Probe:** deterministic: `grep -n sandbox-proxy-ready packages/react/src/mcp-apps/app-frame.tsx` → `121:`; `grep -n teardownResource packages/react/src/mcp-apps/app-frame.tsx` → `140:`; `grep -n "location?.origin ?? 'null'" packages/react/src/mcp-apps/app-frame.tsx` → `24:`; `grep -c 'initializedRef.current = false' packages/react/src/mcp-apps/app-frame.tsx` → `2`. Direct tests: `app-frame.test.tsx` permission-delegation suites :65–91.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "deriveTargetOrigin", limit: 10, fields: ["signature","name","file"] });
// verified live @9d9a73f: rank#1 app-frame.deriveTargetOrigin :19-26
```

## Verdict
Adopt the proxy-pull bootstrap (proxy asks, host answers) and ref-mirrored replay pattern; adapt the effect dependency set to your framework's lifecycle; omit nothing — a port that pushes HTML before `sandbox-proxy-ready` or skips teardown ordering breaks both boot and cleanup.
