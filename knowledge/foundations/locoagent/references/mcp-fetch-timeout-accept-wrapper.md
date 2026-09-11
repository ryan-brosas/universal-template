<!-- capsule-v2 -->
# Fresh-timeout fetch wrappers — how do I keep per-request timeouts from killing long-lived MCP streams?

**Source:** locoagent MIT `main@c01bb3f8`; Codebase Memory `locoagent`. **Question:** Why does one AbortSignal.timeout created at connection time break every request after 60 seconds, and what is the correct wrapper composition?

## Per-request controller + GET exemption + Accept-header guarantee
**Path/Symbol:** `src/services/mcp/client.ts`:`wrapFetchWithTimeout` (:492-550), consts `MCP_REQUEST_TIMEOUT_MS = 60000` (:463), `MCP_STREAMABLE_HTTP_ACCEPT = 'application/json, text/event-stream'` (:471).
**Signature:** `wrapFetchWithTimeout(baseFetch: FetchLike): FetchLike`.
**Data Shape:** Skips timeout entirely for `GET` (those are the long-lived SSE receive streams); normalizes headers through `new Headers(init?.headers)` and sets `accept` only if absent.

### Decisive source
```ts
// Use setTimeout instead of AbortSignal.timeout() so we can clearTimeout on
// completion. AbortSignal.timeout's internal timer is only released when the
// signal is GC'd, which in Bun is lazy — ~2.4KB of native memory per request
// lingers for the full 60s even when the request completes in milliseconds.
const controller = new AbortController()
const timer = setTimeout(c => c.abort(new DOMException('The operation timed out.', 'TimeoutError')),
                         MCP_REQUEST_TIMEOUT_MS, controller)
timer.unref?.()
const parentSignal = init?.signal
const abort = () => controller.abort(parentSignal?.reason)
parentSignal?.addEventListener('abort', abort)
if (parentSignal?.aborted) controller.abort(parentSignal.reason)
const cleanup = () => { clearTimeout(timer); parentSignal?.removeEventListener('abort', abort) }
try {
  const response = await baseFetch(url, { ...init, headers, signal: controller.signal })
  cleanup(); return response
} catch (error) { cleanup(); throw error }
```

**Flow:** POST to transport → wrapper guarantees the Streamable-HTTP dual Accept value survives object-spread header loss (SDK attaches it to Headers that some runtimes drop before the wire; see anthropics/claude-agent-sdk-typescript#202 cited in-source) → fresh 60s timer per request → parent (call-level) abort propagates as reason-carrying abort → cleanup always runs.
**Invariant:** The SSE EventSource path must be constructed with a fetch that does NOT pass through this wrapper (`eventSourceInit.fetch` at :643-671) — applying a 60s timeout there kills the persistent event stream by design. Auth-related requests use a SEPARATE wrapper (`createAuthFetch`, auth.ts) with its own 30s constant so the two timeout budgets stay independent.
**Probe:** `grep -n "if (!headers.has('accept'))" src/services/mcp/client.ts` (`508:`) and `grep -n "if (method === 'GET')" src/services/mcp/client.ts` (`498:`) and `grep -n 'timer.unref?.()' src/services/mcp/client.ts` (`523:`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "wrapFetchWithTimeout", limit: 5 });
```

## Verdict
Adopt per-request fresh timers with manual clearTimeout + unref, the GET exemption for SSE receive streams, and the last-wrapper Accept normalization. Adapt timeout constants. Omit Bun-specific memory commentary beyond keeping unref+clearTimeout.
