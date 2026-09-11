<!-- capsule-v2 -->
# Webworker lifecycle & hidden-tab restart — how does a message worker self-heal from dead senders, auth loss, and 30-minute hidden tabs?

**Source:** OpenReplay AGPL-3.0 `main@99eb60032f70906f6887195c400f173c00a08522`; Codebase Memory `openreplay`. **Question:** What is the worker↔main-thread control protocol that recovers the pipeline without losing buffered messages?

## worker index.ts onmessage / initiateRestart / reset
**Path/Symbol:** `tracker/tracker/src/webworker/index.ts:self.onmessage` (:141-258), `initiateRestart` (:123-130), `initiateFailure` (:132-135), `reset` (:107-121), `WorkerStatus` enum (:12-18).
**Signature:** `onmessage({data}: {data: ToWorkerData})` handling `'stop' | 'forceFlushBatch' | 'closing' | Start | Auth | Message[] | compressed | uncompressed`.
**Data Shape:** Module-level `sender: QueueSender|null`, `writer: BatchWriter|null`, `workerStatus` FSM (NotActive/Starting/Stopping/Active/Stopped); `AUTO_SEND_INTERVAL = 30*1000` keepalive flush; main thread protocol strings `a_stop`/`a_start`/`not_init`.

### Decisive source
```ts
if (Array.isArray(data)) {
    if (writer) {
      data.forEach((message) => {
        if (message[0] === MType.SetPageVisibility) {
          if (message[1]) {   // .hidden → arm a 30-min self-destruct
            restartTimeoutID = setTimeout(() => initiateRestart(), 30 * 60 * 1000)
          } else {
            clearTimeout(restartTimeoutID)  // visible again → disarm
          }
        }
        w.writeMessage(message)
      })
    } else { postMessage('not_init'); initiateRestart() }
```
```ts
function initiateRestart(): void {
  if ([WorkerStatus.Stopped, WorkerStatus.Stopping].includes(workerStatus)) return
  postMessage('a_stop')
  reset().then(() => { postMessage('a_start') })
}
```

**Flow:** main thread owns the restart loop — worker posts `a_stop`/`a_start` hints and the App layer recreates everything on `a_start`. Inside the worker: `stop` → finalize (flush all batches) then reset to Stopped; `closing` (page unload) → finalize with skipCompression=true (sendBeacon-style path must not wait for gzip); sender-not-initialised while receiving compressed/uncompressed/auth → initiateRestart instead of crashing; failure path posts `{type:'failure', reason}` and resets. A 30 s setInterval calls finalize() so idle sessions still emit keepalive batches.
**Invariant:** Restart is IDEMPOTENT and re-entrancy-guarded by WorkerStatus — Stopped/Stopping swallow new restart requests so a dying worker can't loop. The hidden-tab timer exists because browsers throttle/suspend workers in background tabs: after 30 minutes hidden the session is presumed stale and is deliberately recycled rather than left half-alive. Every teardown finalizes pending batches BEFORE dropping references, so restart loses at most in-flight network state, never encoded bytes.
**Probe:** `grep -n '30 \* 60 \* 1000' tracker/tracker/src/webworker/index.ts` from repo root → line 165 (verified live); `grep -n 'AUTO_SEND_INTERVAL' tracker/tracker/src/webworker/index.ts` → lines 20 and 235. Coverage caveat: this file has no dedicated jest suite — behavior pinned via QueueSender/BatchWriter batteries + source reading.
**Retrieve:** search_graph project openreplay query "initiateRestart workerStatus reset WorkerStatus" → rank-1 Enum `WorkerStatus :12-18`, Function `initiateRestart :123-130` line-exact.

## Verdict
Adopt the status-FSM restart guard, visibility-armed recycle timer, and finalize-before-teardown ordering as pure lifecycle behavior; adapt postMessage string protocol (`a_stop`/`a_start`) to your RPC channel; omit the debug batch-type reader (debugReadBatchTypes) if you don't need wire introspection.
