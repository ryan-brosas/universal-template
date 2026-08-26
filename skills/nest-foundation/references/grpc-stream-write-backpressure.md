<!-- capsule-v2 -->
# gRPC stream write-out backpressure — how do you pipe an Rx stream into a backpressured Writable without losing error ordering or turning client-cancel into a failure?

**Source:** nest (MIT) `master@4c38a5ab100f`; Codebase Memory `nest`. **Question:** How do you write an Observable to a gRPC/Node Writable that can signal `write() === false`, while guaranteeing errors and `end()` land in the right order and a client cancellation resolves instead of rejecting?

## The never-rejecting write machine
**Path/Symbol:** `packages/microservices/server/server-grpc.ts:ServerGrpc.writeObservableToGrpc` (352-448); companion pre-handler buffer `ServerGrpc.bufferUntilDrained` (737-808).
**Signature:** `private writeObservableToGrpc<T>(source: Observable<T>, call: GrpcCall<T>): Promise<void>`; `bufferUntilDrained<T>(): { subject, next, error, complete, cleanup }`.
**Data Shape:** internal state: `valuesWaitingToBeDrained: T[]` (buffer while unwritable), `shouldErrorAfterDraining`/`shouldResolveAfterDraining` deferred-terminal latches, `writing: boolean` (mirrors the last `call.write()` return), one RxJS `Subscription` owning ALL teardown.

### Decisive source
```ts
return new Promise((resolve, _doNotUse) => {          // **never rejects**
  const valuesWaitingToBeDrained: T[] = [];
  let shouldErrorAfterDraining = false; let error: any;
  let shouldResolveAfterDraining = false; let writing = true;
  const subscription = new Subscription();

  const cancelHandler = () => { subscription.unsubscribe(); resolve(); }; // cancel ⇒ success
  call.on(CANCELLED_EVENT, cancelHandler);
  subscription.add(() => call.off(CANCELLED_EVENT, cancelHandler));
  subscription.add(() => call.end());                  // end() AFTER writes/errors by teardown order

  const drain = () => {
    writing = true;
    while (valuesWaitingToBeDrained.length > 0) {
      const value = valuesWaitingToBeDrained.shift();
      if (writing) {
        writing = call.write(value);
        if (!writing) return;                          // wait for next 'drain'
      }
    }
    if (shouldResolveAfterDraining) { subscription.unsubscribe(); resolve(); }
    else if (shouldErrorAfterDraining) { call.emit('error', error); subscription.unsubscribe(); resolve(); }
  };
  call.on('drain', drain);

  subscription.add(source.subscribe({
    next(value) { writing ? (writing = call.write(value)) : valuesWaitingToBeDrained.push(value); },
    error(err) {
      if (valuesWaitingToBeDrained.length === 0) { call.emit('error', err); subscription.unsubscribe(); resolve(); }
      else { shouldErrorAfterDraining = true; error = err; }   // deferred until drained
    },
    complete() {
      if (valuesWaitingToBeDrained.length === 0) { subscription.unsubscribe(); resolve(); }
      else { shouldResolveAfterDraining = true; }              // end only after buffer drains
    },
  }));
});
```

**Flow:** values write directly while `writing === true`; the first `false` return flips the latch and every later value buffers; each `drain` event re-opens the loop and flushes buffered values until another `false`; completion/error arriving mid-buffer are DEFERRED (flags + captured error) so the wire sees all data before `error`/`end`; the `cancelled` event tears down the source subscription and resolves the promise successfully — a client hang-up is not an error. The promise exists only to signal drain completion; failures surface exclusively through `call.emit('error')`.
**Invariant:** the promise NEVER rejects; no value is written after `end()` (teardown order guarantees it); errors are emitted at most once and only after all buffered values drained.
**Probe:** `packages/microservices/test/server/server-grpc.spec.ts` createCall fixture (`highwaterMark=2`): `'a','b'` written, `'c'..'e'` buffered across two drains, `complete()` during buffering ends only after the buffer drains (`[..., 'e', 'end']`), `cancel()` unsubscribes the subject (`subject.observed === false`) and still ends the call, deferred error surfaces via `call.emit('error', err)` after final drain.
**Runner caveat:** direct test execution blocked (deps uninstalled); expectations quoted from spec source read directly.

## Pre-handler request-stream buffer (companion)
**Path/Symbol:** `bufferUntilDrained` returns a Proxy over a `Subject`; before "drain", property reads forward to a `ReplaySubject` so messages arriving while async guards/interceptors delay handler execution are buffered; `next/error/complete` mirror into both buffers; `asObservable()` grafts `drainBuffer` onto the returned stream (replays into the live subject on `setImmediate`, then nulls the replay buffer); `cleanup()` (wired to call `end`) drops an undrained buffer.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nest", name_pattern: "writeObservableToGrpc|bufferUntilDrained", fields: ["lines"], limit: 10 });
// live @ pin: rank#1 ServerGrpc.bufferUntilDrained 737-808, rank#2 ServerGrpc.writeObservableToGrpc 352-448
```

## Verdict
Adopt the four-state writable machine (direct-write / buffered / deferred-error / deferred-complete) plus "cancel resolves successfully" verbatim for ANY Observable→Writable bridge with flow control; adapt the event names (`drain`, `cancelled`) to your stream API's equivalents and keep "terminal events wait for the buffer" even if your transport lacks backpressure signals. Omit the ReplaySubject pre-handler proxy unless your pipeline can delay handler attachment behind async enhancers — then keep its cleanup-on-end semantics so an aborted call never replays stale buffers.
