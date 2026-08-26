<!-- capsule-v2 -->
# SSE lifecycle + heartbeat contract — how do long check/repair streams survive proxies and report failures without breaking the event grammar?

**Source:** teable AGPL `develop@06a4461e`; Codebase Memory `teable`. **Question:** What must a porter reproduce so integrity streams neither stall nor emit protocol-invalid events?

## runSseStream family
**Path/Symbol:** `apps/nestjs-backend/src/features/integrity/integrity-v2.controller.ts:runSseStream` (:205–239), `:prepareSseResponse` (:240–259), `:startHeartbeat` (:260–273), `:sendSseEvent` (:274–283), `:isStreamClosed` (:284–287), lifecycle factories (:288–350); routes :80–204.
**Signature:** `runSseStream<T extends {id:string}>(res, {createStream, createConnectEvent, createCompleteEvent, createErrorEvent})`.
**Data Shape:** Every event satisfies the result VO: `{id, fieldId:'', fieldName:'', ruleId, ruleDescription, status, message, required:true, timestamp, dependencies:[], depth:0}`; repair events add `outcome` (`'manual'` on error, `'unchanged'` on complete).

### Decisive source
```ts
const heartbeat = this.startHeartbeat(res);
try {
  this.sendSseEvent(res, options.createConnectEvent());
  if (!this.cls.get('useV2')) {
    this.sendSseEvent(res, options.createErrorEvent('V2 schema integrity is not enabled'));
    return;                       // finally still clears interval + res.end()
  }
  const stream = await options.createStream();
  for await (const result of stream) {
    if (this.isStreamClosed(res)) break;
    this.sendSseEvent(res, result);
  }
  this.sendSseEvent(res, options.createCompleteEvent());
} catch (error) {
  this.sendSseEvent(res, options.createErrorEvent(this.getErrorMessage(error)));
} finally {
  clearInterval(heartbeat);
  res.end();
}
```
```ts
res.write(': ping\n\n');          // comment-line heartbeat every sseHeartbeatMs = 15_000
```

**Flow:** Headers first (`text/event-stream`, `no-cache, no-transform`, `X-Accel-Buffering: no`, feature/reason headers) → connect event → gated stream → per-result write with closed-check → complete OR error event (error keeps status 'error' + ruleId 'unexpected'; repair errors carry outcome 'manual', completes 'unchanged') → always clear heartbeat + end. Heartbeat writes an SSE COMMENT (not data) and re-checks closed state.
**Invariant:** Errors are DATA EVENTS on the same stream (client-parsable), never raw HTTP failures mid-stream — but only AFTER headers; the connect/complete/error trio uses reserved ids ('connect','complete','error:unexpected') and empty fieldId so clients can discriminate lifecycle from results. Flush after every write (`flushable.flush?.()`) because compression middleware otherwise buffers.
**Probe:** `grep -cF 'sseHeartbeatMs = 15_000' apps/nestjs-backend/src/features/integrity/integrity-v2.controller.ts` → 1; `grep -cF 'X-Accel-Buffering' <same>` → 1.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "runSseStream startHeartbeat prepareSseResponse", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt comment-heartbeat + lifecycle-event grammar + error-as-event; adapt header set to your proxy chain; omit V2 gating flags.
