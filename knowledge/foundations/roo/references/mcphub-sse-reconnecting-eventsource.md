<!-- capsule-v2 -->
# SSE reconnecting EventSource swap — how do you give the MCP SDK's SSE transport automatic reconnection without losing custom headers?

**Source:** Roo-Code (Roo Code, Inc.) Apache-2.0 `main@b867ec9145750d0ae1ff7f02d35406e9bf2a0b16`; Codebase Memory `Roo-Code`. **Question:** How does the hub wire `reconnecting-eventsource` into `SSEClientTransport` while still injecting per-server Authorization/headers on every (re)connect attempt?

## Global EventSource replacement + fetch wrapper that re-applies headers
**Path/Symbol:** `src/services/mcp/McpHub.ts` (`connectToServer` sse arm :807–830).
**Signature:** `transport = new SSEClientTransport(new URL(configInjected.url), { ...sseOptions, eventSourceInit: reconnectingEventSourceOptions })`.
**Data Shape:** `eventSourceInit` = `{ max_retry_time: 5000, withCredentials: !!headers["Authorization"], fetch: (url, init) => fetch(url, { ...init, headers: new Headers({ ...(init?.headers || {}), ...(configInjected.headers || {}) }) }) }`.

### Decisive source
```ts
// :815-826
const reconnectingEventSourceOptions = {
    max_retry_time: 5000, // Maximum retry time in milliseconds
    withCredentials: configInjected.headers?.["Authorization"] ? true : false,
    fetch: (url: string | URL, init: RequestInit) => {
        const headers = new Headers({ ...(init?.headers || {}), ...(configInjected.headers || {}) })
        return fetch(url, { ...init, headers })
    },
}
global.EventSource = ReconnectingEventSource
```

**Flow:** build options → REPLACE `global.EventSource` with ReconnectingEventSource (the SDK constructs its internal ES via the global, so this is the injection point) → construct SSEClientTransport with both `requestInit.headers` (for the initial POST-based flow) and `eventSourceInit` (for the GET stream + reconnects) → standard onerror/onclose handlers append errors and notify.
**Invariant:** headers must be merged inside the CUSTOM FETCH, not only in requestInit — reconnect attempts create NEW EventSource requests whose init headers would otherwise lack Authorization; `withCredentials` is derived strictly from Authorization presence. The global assignment is process-wide: acceptable here because every SSE server wants reconnecting behavior; a port with mixed requirements must scope it differently.
**Probe:** no dedicated upstream unit spec isolates the sse arm at this pin (the Windows-wrapping and timeout suites cover stdio arms); coverage caveat — deterministic probe pins the source shape:
`grep -c 'global.EventSource = ReconnectingEventSource' src/services/mcp/McpHub.ts` = **1** (exact assignment site :826), and `grep -c 'max_retry_time' src/services/mcp/McpHub.ts` = **1** (:816).

## Get live surrounding code
**Retrieve:** (drift note 2026-08-24 pass 7: original multi-token query "SSEClientTransport ReconnectingEventSource max_retry_time" regressed to total:0 under pass-17-class BM25 noise-label filtering — adjudicated wrong-plane, repaired to the two primitives below, both live-resolved)
```ts
await mcp.codebase_memory.search_graph({ project: "Roo-Code", query: "connectToServer", limit: 5 });
// rank#1 Method McpHub.connectToServer src/services/mcp/McpHub.ts 655-896 carries the sse arm
```
```bash
codebase-memory-mcp cli search_code '{"project":"Roo-Code","pattern":"ReconnectingEventSource"}'
# resolves the assignment ITSELF line-exact: connectToServer Method rows at 814;826 (+ Module row)
```

## Verdict
Adopt the fetch-wrapper header merge + global ES swap as one unit. Adapt `max_retry_time` to your fleet's tolerance. Omit nothing — dropping the fetch wrapper silently de-auths reconnects.
