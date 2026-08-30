<!-- capsule-v2 -->
# RouterResponseController.sse — the SSE terminal-state machine: settled latch, finalize funnel, disconnect-vs-producer races

**Source:** nest MIT `master@61b03510`; Codebase Memory `nest`. **Question:** How does the SSE writer stay correct across client disconnect, producer error, completion, and an async handler that resolves after any of them?

## sse lifecycle
**Path/Symbol:** `packages/core/router/router-response-controller.ts:sse` (:103-290), `finalize` (:151-154), `onClose` (:162-180).
**Signature:** `async sse<TInput extends Observable, TResponse, TRequest>(result: TInput | Promise<TInput>, response, request, options?: { additionalHeaders?, statusCode? }): Promise<void>`.
**Data Shape:** three mutable flags — `settled` (promise resolved/rejected once), `closeRequested` (disconnect seen), `subscription`; plus per-request `AbortController` carried on the request under symbol key.

### Decisive source
```ts
if (response.writableEnded) {                       // already gone pre-subscribe
  this.getOrCreateAbortController(request).abort(); // still release handler resources
  Promise.resolve(result).catch(err => this.logger.error(err)); // swallow late rejection
  return;
}
const onClose = () => {
  if (settled || closeRequested) return;
  closeRequested = true;
  if (!subscription) { finalize(); return; }        // disconnect before subscribe
  settled = true; finalize();
  subscription?.unsubscribe(); endStream(); response.end(); resolve();
};
disconnectSource.once('close', onClose);
Promise.resolve(result).then(observableResult => {
  ...
  if (closeRequested) { settled = true; endStream(); response.end(); resolve(); return; }
  stream.pipe(response, {...});
  subscription = observableResult.pipe(/* map→MessageEvent, concatMap(writeMessage),
      catchError → in-band error event when headers committed */).subscribe({...});
  setTimeout(() => { if (!settled) stream.commitHeaders(); }, 0); // macrotask commit
}).catch(err => { /* closeRequested → quiet resolve, else settled=true+finalize+reject */ });
```

**Flow:** early-out on ended responses (abort + swallow) → register socket-close listener → resolve async result → if client already gone, never subscribe the producer → else pipe SseStream and subscribe with error/complete handlers → EVERY terminal path funnels through `finalize()` (remove close listener + `abortController.abort()`), then `endStream()` + resolve/reject.
**Invariant:** (1) The producer Observable is NEVER subscribed after a disconnect — subscribing just to abort starts side effects to cancel them. (2) Headers commit on a MACROTASK so pipe-validation microtask errors can still change status via filters before anything is sent (`headersCommitted` gate). (3) `finalize` runs exactly once per lifecycle and abort is idempotent — normal completion ALSO aborts the signal, so @SseSignal cleanup fires on every exit path. (4) Producer errors AFTER headers are converted to in-band SSE error events; before headers they reject.
**Probe:** `packages/core/test/router/router-response-controller.spec.ts` ("should not subscribe async SSE producer Observable when client disconnects mid-await (interceptor case, issue #17352)", "should abort the per-request SSE AbortSignal when the client disconnects", "should not write headers or events after the socket closes...").

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nest", query: "RouterResponseController sse transformToResult getStatusByMethod", limit: 5 });
```

## Verdict
Adopt the settled/closeRequested/finalize state machine wholesale for any long-lived response streaming; adapt transport specifics (socket vs writable close events); omit the in-band error event only if you always reject. Porting wrong: awaiting the handler promise before checking disconnect reintroduces issue #17352; committing headers synchronously freezes status codes before validation errors surface.
