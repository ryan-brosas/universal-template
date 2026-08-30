<!-- capsule-v2 -->
# Airtable SSE import streaming — what does a long-running import endpoint owe its HTTP client?

**Source:** teable AGPL `develop@06a4461e`; Codebase Memory `teable`. **Question:** How is the SSE stream framed, kept alive, closed, and made proxy-safe?

## Event-stream framing in the controller
**Path/Symbol:** `apps/nestjs-backend/src/features/airtable-import/airtable-import.controller.ts`:`importStream` (:88–151).
**Signature:** `async importStream(@Body(...) importAirtableRo, @Res() res: ExpressResponse)`.
**Data Shape:** three event kinds on one grammar — `{type:'progress', ...}`, `{type:'done', data}`, `{type:'error', message}`; heartbeat = SSE comment line `: ping`; 15 s interval.

### Decisive source
```ts
const sseHeartbeatMs = 15_000;
res.setHeader('Content-Type', 'text/event-stream');
res.setHeader('Cache-Control', 'no-cache, no-transform');
res.setHeader('Connection', 'keep-alive');
res.setHeader('X-Accel-Buffering', 'no');   // nginx: flush through, don't buffer
res.flushHeaders();
const isStreamClosed = () => res.writableEnded || res.destroyed;
const sendEvent = (data: unknown) => {
  if (isStreamClosed()) return;
  res.write(`data: ${JSON.stringify(data)}\n\n`);
  (res as ... & { flush?: () => void }).flush?.();
};
const heartbeat = setInterval(() => { if (isStreamClosed()) return; res.write(': ping\n\n'); ...
}, sseHeartbeatMs);
res.on('close', () => clearInterval(heartbeat));
```

**Flow:** authorize FIRST (see airtable-import-authz capsule) → set headers + flush → run importBase with a progress reporter that writes events → done/error as final event → finally clears the heartbeat and ends the response. Every write checks `isStreamClosed()` first; errors become typed error EVENTS (HTTP status already 200), with the raw reason logged server-side including base/target ids.
**Invariant:** The failure contract lives INSIDE the stream — after headers are sent you cannot change status codes, so `formatAirtableImportError` maps provider errors to human guidance (401 ⇒ token invalid; 403/404 ⇒ scope/base-access hint). Heartbeats keep intermediaries from timing out a silent import; the close listener prevents timer leaks.
**Probe:** `grep -cF "X-Accel-Buffering" apps/nestjs-backend/src/features/airtable-import/airtable-import.controller.ts` returns 1; `grep -cF ": ping" apps/nestjs-backend/src/features/airtable-import/airtable-import.controller.ts` returns 1.

## Get live surrounding code
**Retrieve:**
```bash
codebase-memory-mcp cli search_graph '{"project":"teable","query":"importStream sseHeartbeatMs sendEvent formatAirtableImportError","limit":5,"detail":"ids"}'
```

## Verdict
Adopt the header set, comment-line heartbeat, closed-stream guard, and in-stream error typing for any long-operation SSE endpoint; adapt event vocabulary; omit teable's logger wiring. Coverage caveat: none.
