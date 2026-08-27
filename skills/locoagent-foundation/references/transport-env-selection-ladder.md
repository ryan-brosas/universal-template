<!-- capsule-v2 -->
# Env-gated transport selection — which read/write topology does a remote session URL get, and how is the SSE URL derived from a ws:// URL?

**Source:** locoagent MIT `main@c01bb3f8`; Codebase Memory `locoagent`. **Question:** Given one session URL plus deployment flags, which transport class is constructed, and what URL surgery precedes SSE construction?

## Selection ladder in getTransportForUrl
**Path/Symbol:** `src/cli/transports/transportUtils.ts`: `getTransportForUrl` (:16-45).
**Signature:** `(url: URL, headers?: Record<string,string>, sessionId?: string, refreshHeaders?: () => Record<string,string>) => Transport`.
**Data Shape:** Priority: (1) `CLAUDE_CODE_USE_CCR_V2` truthy ⇒ SSETransport regardless of URL scheme — session URL `.../sessions/{id}` gets pathname suffix `/worker/events/stream` and `wss:`→`https:` /`ws:`→`http:` rewrite; (2) ws:/wss: URL + `CLAUDE_CODE_POST_FOR_SESSION_INGRESS_V2` ⇒ HybridTransport; (3) ws:/wss: otherwise ⇒ WebSocketTransport; (4) any other protocol ⇒ throw.

### Decisive source
```ts
if (isEnvTruthy(process.env.CLAUDE_CODE_USE_CCR_V2)) {
  // v2: SSE for reads, HTTP POST for writes
  const sseUrl = new URL(url.href)
  if (sseUrl.protocol === 'wss:') { sseUrl.protocol = 'https:' }
  else if (sseUrl.protocol === 'ws:') { sseUrl.protocol = 'http:' }
  sseUrl.pathname = sseUrl.pathname.replace(/\/$/, '') + '/worker/events/stream'
  return new SSETransport(sseUrl, headers, sessionId, refreshHeaders)
}
if (url.protocol === 'ws:' || url.protocol === 'wss:') {
  if (isEnvTruthy(process.env.CLAUDE_CODE_POST_FOR_SESSION_INGRESS_V2)) {
    return new HybridTransport(url, headers, sessionId, refreshHeaders)
  }
  return new WebSocketTransport(url, headers, sessionId, refreshHeaders)
} else { throw new Error(`Unsupported protocol: ${url.protocol}`) }
```

**Flow:** flag check → scheme-aware construction; CCR v2 wins even for ws URLs because the flag redefines the wire contract, not just the class.
**Invariant:** Protocol rewrite MUST precede pathname surgery (an https URL with ws-style path is valid; a wss URL handed to fetch is not). Non-ws protocols are rejected unless the CCR flag redefines them. The consumer (`src/cli/remoteIO.ts`:88,117-123) re-asserts the result is SSETransport under CCR v2 — defense in depth against silent ladder edits.
**Probe:** `grep -n "CLAUDE_CODE_USE_CCR_V2" src/cli/transports/transportUtils.ts` (`:22`), `grep -n "worker/events/stream" src/cli/transports/transportUtils.ts` (`:33`), `grep -n "Unsupported protocol" src/cli/transports/transportUtils.ts` (`:43`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "getTransportForUrl", limit: 5 });
```

## Verdict
Adopt the three-topology ladder and derive-don't-store URL rewriting. Adapt flag names and path suffixes to your ingress. Omit the throw for exotic schemes only if you have a fourth topology.
