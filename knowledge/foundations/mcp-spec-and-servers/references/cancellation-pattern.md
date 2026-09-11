<!-- capsule-v2 -->
# Cancellation (notifications/cancelled) — who may cancel what, per transport, and which races must both sides survive?

**Source:** modelcontextprotocol/specification MIT `main@4df2d6b6`; Codebase Memory `modelcontextprotocol`. **Question:** When is `notifications/cancelled` required vs forbidden, how does each transport signal cancel, and what does a server do on late-arriving cancellations?

## Fire-and-forget notification; transport decides whether it's even needed
**Path/Symbol:** `docs/specification/2026-07-28/basic/patterns/cancellation.mdx` (whole page, 122L: MUST-scope :11–14; flow+payload :16–33; transport-specific :35–55 incl. timeouts; behavior requirements :66–82; timing races :84–104; error handling :111–120).

**Signature:** `{ method: "notifications/cancelled", params: { requestId, reason? } }` — a NOTIFICATION (no response ever). `requestId` references a previously issued, believed-in-flight request.

**Data Shape:** `reason` optional, for logging/display only.

### Decisive source
```md
# cancellation.mdx:11-14 + 35-43 (the asymmetric scope rule)
A server **MUST** send `notifications/cancelled` referencing a
`subscriptions/listen` request ID when it tears down that subscription stream.
Servers **MUST NOT** send `notifications/cancelled` for any other purpose.
...
- **Streamable HTTP**: Closing the SSE response stream is the cancellation signal.
  The server **MUST** treat a client disconnect as cancellation of that request. No
  `notifications/cancelled` message is required or expected.
- **stdio**: There is no per-request stream to close. The client **MUST** send a
  `notifications/cancelled` notification referencing the request ID.
```

**Flow:** client cancels ⇒ HTTP: close the SSE response stream (that IS the signal); stdio: emit the notification with the request id → receiver SHOULD stop processing, free resources, and NOT answer → client SHOULD ignore any late response → timeouts follow the same ladder (HTTP = close the stream; stdio = send the notification); progress notifications MAY reset the timeout clock but implementations SHOULD still enforce a maximum ceiling.

**Invariants:**
1. **Server→client cancellations have exactly ONE legal use**: terminating its own `subscriptions/listen` stream. A porter reusing them to abort server-initiated requests breaks the protocol.
2. **HTTP disconnect = cancellation by definition** — servers MUST honor it without expecting any notification; stdio has no such channel, hence the notification there.
3. **Races are normative**: cancellations may arrive after completion/response; receivers MAY ignore unknown/completed/uncancellable requests, and invalid ones are ignored silently ("fire and forget").
4. Cancelled requests get NO error response — absence of response plus client-side ignore of stragglers is the contract.

**Probe:** no runtime tests in the spec repo; machine-checkable anchors: `CancelledNotification` wire type in the schema and the stdio page's cancellation section (:76–85) mirrored in `stdio-transport.md`. Coverage caveat recorded honestly.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "modelcontextprotocol", name_pattern: "CancelledNotification|notifications/cancelled", limit: 10 });
```

## Verdict
Adopt the transport-split signaling (stream-close vs notification), the single-purpose server-side rule, race-tolerant silent ignoring, and timeout-as-cancellation with progress-aware but capped clocks; adapt timeout values to your workload; omit nothing — every clause here is load-bearing wire behavior. Fills the gap left by `stdio-transport.md`, which cites this surface only from the legacy-era angle.
