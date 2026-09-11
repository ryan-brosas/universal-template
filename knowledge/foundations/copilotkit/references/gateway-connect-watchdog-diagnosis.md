<!-- capsule-v2 -->
# Gateway connect watchdog & HTTP endpoint diagnosis — why does a wrong wsUrl hang forever, and how do you name the cause?

**Source:** copilotkit MIT `main@e9387e04835545c45744b791aee7c9c03520be31`; Codebase Memory `ext-copilotkit`. **Question:** Phoenix retries a failed first connect forever and its join-push timeout never fires — how does the client distinguish "host doesn't exist" from "still booting" and fail with a USEFUL error?

## everConnected-keyed watchdog + unauthenticated fetch probe (OSS-623)
**Path/Symbol:** `packages/channels-intelligence/src/realtime-gateway.ts:connectRealtimeGateway` (:577-1163); watchdog block :607-794; `diagnoseEndpoint` (:420-480), `toHttpProbeUrl` (:488-504), `NON_RETRYABLE_TRANSPORT_CODES` (:353-356), `RealtimeGatewayUnreachableError` (:242-281).
**Signature:** `async function diagnoseEndpoint(wsUrl: string, timeoutMs: number, fetchImpl?: typeof globalThis.fetch): Promise<EndpointDiagnosis | undefined>`; config windows `connectTimeoutMs` (default 30s), `reconnectGiveUpMs` (default 60s), probe budget `Math.min(3_000, connectTimeoutMs)`.
**Data Shape:** diagnosis = `{ text, code?, nonRetryable, status?, cause? } | undefined`; only NXDOMAIN-class codes (`ENOTFOUND`, `EAI_NONAME`) are non-retryable — `ECONNREFUSED`/`EAI_AGAIN`/`ETIMEDOUT` deliberately stay in the window.

### Decisive source
```typescript
// WHY the cause comes from an HTTP probe and not from the socket (:622-630):
// Node's global WebSocket dispatches an identical, detail-free error for a host
// that does not resolve, a refused port, and a host answering HTTP with no
// socket mounted — so the transport error alone can neither name the cause nor
// tell a permanent misconfiguration from a gateway that is still booting.
connectDeadline = setTimeout(() => {
  connectDeadline = undefined;
  if (!everConnected) failUnreachable();
}, connectTimeoutMs);

const response = await fetchImpl(httpUrl, {
  method: "GET",
  redirect: "manual",          // keep redirects visible as statuses
  ...(signal ? { signal } : {}),
});
// No auth header: reachability probe; token belongs on the socket handshake only.
```

**Flow:** socket opens → `everConnected = true` clears the deadline → socket never opens + window elapses → `failUnreachable()` tears the socket down synchronously (marked intentional) then awaits/kicks the memoized probe → NXDOMAIN verdict short-circuits the window immediately (`startDiagnosis`'s `.then` calls `failUnreachable`) → reject with `RealtimeGatewayUnreachableError` carrying endpoint (query stripped) + probe text + `retryable` classification. A transport that DOES expose OS codes (`ws` package) is trusted directly and skips the probe (`if (detail.code === undefined) probeOutage()`). Healthy connects issue NO extra request (probe runs on failure path only).
**Invariant:** The join push's own timeout cannot save you here — `Channel.onError` calls `joinPush.reset()` while joining, detaching the reply binding the armed timeout would have triggered (:608-614). Everything keys off "has the socket EVER opened": never-opened = unreachable host (reject), opened-then-dropped = reconnect episode owned by the health FSM.
**Probe:** `packages/channels-intelligence/src/realtime-gateway.test.ts` :998 "fails immediately when the HTTP diagnosis shows the host does not resolve"; :1047 "waits out the connect window when the host merely refuses"; :1102 "trusts a transport that exposes the OS code, without probing"; :1237 "issues no diagnostic request at all when the connect succeeds". Deterministic anchor `grep -n "NON_RETRYABLE_TRANSPORT_CODES" packages/channels-intelligence/src/realtime-gateway.ts`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-copilotkit", query: "diagnoseEndpoint failUnreachable everConnected RealtimeGatewayUnreachableError", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the watchdog + same-origin-HTTP-probe pattern for ANY Phoenix/socket client whose transport hides failure causes. Adapt the non-retryable code set to your platform's DNS errors. Omit auth headers from the probe — a 401 there proves nothing about credential validity (unauthenticated GET is refused either way).
