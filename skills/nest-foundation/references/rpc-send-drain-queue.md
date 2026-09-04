<!-- capsule-v2 -->
# RPC send drain queue — how does a server emit broker responses serially without losing the terminal marker?

**Source:** nest (MIT) `master@4c38a5ab100f`; Codebase Memory `nest`. **Question:** How do you deliver an Observable handler's emissions, errors, and completion to an async respond() callback in order, exactly once per tick, even when the stream errors?

## One nextTick drain loop with dispose coalescing
**Path/Symbol:** `packages/microservices/server/server.ts:Server.send` (172-206).
**Signature:** `send(stream$: Observable<any>, respond: (data: WritePacket) => Promise<unknown> | void): Subscription`.
**Data Shape:** internal `dataQueue: WritePacket[]` + `isProcessing` latch; packets are `{response?}`, `{err?}`, `{isDisposed?: boolean}`.

### Decisive source
```ts
const scheduleOnNextTick = (data: WritePacket) => {
  if (data.isDisposed && dataQueue.length > 0) {
    dataQueue[dataQueue.length - 1].isDisposed = true;   // coalesce terminal marker
  } else {
    dataQueue.push(data);
  }
  if (!isProcessing) {
    isProcessing = true;
    process.nextTick(async () => {
      while (dataQueue.length > 0) {
        const packet = dataQueue.shift();
        if (packet) await respond(packet);
      }
      isProcessing = false;
    });
  }
};
return stream$
  .pipe(
    catchError((err: any) => { scheduleOnNextTick({ err }); return EMPTY; }),
    finalize(() => scheduleOnNextTick({ isDisposed: true })),
  )
  .subscribe((response: any) => scheduleOnNextTick({ response }));
```

**Flow:** every emission/error/completion becomes a queued packet; a single macrotask-less drain (`process.nextTick`) shifts and awaits `respond` sequentially; a bare dispose packet never enqueues — it stamps `isDisposed: true` onto the last queued packet so clients receive e.g. `{response:'test', isDisposed:true}` in ONE call; error streams yield `{err, isDisposed:true}` because catchError emits then finalize fires.
**Invariant:** respond() calls are ordered and never concurrent; the terminal marker is never lost or delivered empty-handed after a real payload; subscription teardown still cancels upstream via the returned Subscription.
**Probe:** `packages/microservices/test/server/server.spec.ts` (send() tests await `process.nextTick` then assert `respond` called once with `{err:'test', isDisposed:true}` / `{response:'test', isDisposed:true}`).
**Runner caveat:** direct test execution blocked (deps uninstalled); assertions quoted from spec source.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nest", query: "send stream respond disposed queue", file_pattern: "packages/microservices/server/server.ts", limit: 6 });
// live @ pin: rank#1 Server.send 172-206
```

## Verdict
Adopt the latch-guarded single-drain loop and dispose coalescing verbatim for any request/response-over-broker surface; adapt `process.nextTick` to your runtime's microtask/macrotask equivalent while keeping "drain later than all synchronous scheduling"; omit RxJS plumbing only if your streams differ fundamentally.
