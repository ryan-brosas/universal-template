<!-- capsule-v2 -->
# SDK control_request abort contract — how do you cancel an outstanding host request without hanging either side, and keep control messages from overtaking stream output?

**Source:** locoagent MIT `main@c01bb3f8`; Codebase Memory `locoagent`. **Question:** What is the promise-map + cancel-request algebra for a stdio control plane where the host may never answer and aborts must be instant?

## Cancel-and-reject-now; schema-validate at resolve; one outbound queue
**Path/Symbol:** `src/cli/structuredIO.ts`: `outbound` Stream/:160-162, `prependUserMessage`/:199-213, `read` EOF rejection/:248-261, `injectControlResponse`/:275-309, `sendRequest`/:469-531.
**Signature:** `sendRequest<Response>(request, schema: z.Schema, signal?, requestId = randomUUID()): Promise<Response>`; pending map `Map<request_id, {resolve, reject, schema?, request}>`.
**Data Shape:** wire envelope `{type:'control_request', request_id, request}`; cancellation `{type:'control_cancel_request', request_id}`; resolution arrives as stdin `control_response`.

### Decisive source
```ts
const aborted = () => {
  this.outbound.enqueue({ type: 'control_cancel_request', request_id: requestId })
  // Immediately reject the outstanding promise, without
  // waiting for the host to acknowledge the cancellation.
  const request = this.pendingRequests.get(requestId)
  if (request) {
    // Track the tool_use ID as resolved before rejecting, so that a
    // late response from the host is ignored by the orphan handler.
    this.trackResolvedToolUseId(request.request)
    request.reject(new AbortError())
  }
}
```
```ts
// injectControlResponse (bridge path): feed claude.ai's decision into the SAME
// map AND cancel the SDK consumer's own canUseTool callback — "the bridge won":
this.trackResolvedToolUseId(request.request)
this.pendingRequests.delete(requestId)
void this.write({ type: 'control_cancel_request', request_id: requestId })
if (response.response.subtype === 'error') request.reject(new Error(response.response.error))
else { /* request.schema ? resolve(schema.parse(result)) : resolve({}) */ }
```

**Flow:** sendRequest gates on inputClosed/already-aborted BEFORE enqueueing, enqueues via the shared `outbound` Stream (sendRequest AND print.ts enqueue there; the drain loop is the only writer — "prevents control_request from overtaking queued stream_events"), registers a once-abort listener, awaits the promise keyed in pendingRequests; finally{} removes the listener and the pending entry. read() rejects EVERY remaining pendingRequest at input EOF ("Tool permission stream closed before response received"). prependUserMessage serializes a synthetic user message into prependedLines which the line-splitter re-checks BETWEEN each yielded message so mid-block prepends still land first.
**Invariant:** Abort ⇒ cancel-on-the-wire + IMMEDIATE local rejection (never wait for host ack) + resolved-ID bookkeeping FIRST so the late host answer hits the dedup capsule's orphan filter instead of resolving a dead promise. Resolution validates through the caller's zod schema INSIDE the resolver (schema.parse failure rejects the caller, not the IO loop). Exactly one pending entry per request_id; the finally-block delete makes timeouts/abort paths leak neither listeners nor map slots.
**Probe:** `grep -n "the host to acknowledge" src/cli/structuredIO.ts` (`:496` comment), `grep -n "Track the tool_use ID as resolved before rejecting" src/cli/structuredIO.ts` (`:499`), `grep -n "the bridge won" src/cli/structuredIO.ts` (`:290` comment), `grep -n "Prevents control_request from overtaking" src/cli/structuredIO.ts` (`:161`). No upstream unit tests — deterministic anchors are the probe tier.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", name_pattern: "^(processLine|sendRequest|read)$", file_pattern: "**/structuredIO.ts", limit: 5 });
// processLine :333-463 · read :215-261 · sendRequest :469-531 (executed live pre-write)
```

## Verdict
Adopt for every request/response layer over a fire-and-forget channel. Adapt the wire envelopes to your protocol; keep the ordering cancel → track → reject. Omit injectControlResponse unless a second UI surface shares the same permission flow.
