<!-- capsule-v2 -->
# Stop teardown ordering — in what order do you release mic, queued sends, and the transport so nothing is lost or double-closed?

**Source:** pi-better-openai MIT `main@1188f985389328cff660b6bdbe52f38fdb826c70`; Codebase Memory `pi-better-openai`. **Question:** A voice session has a running recorder, a promise-chained send queue, and an open transport — what is the safe teardown sequence and error-preservation rule?

## Teardown ladder
**Path/Symbol:** `src/live/controller.ts:stop` (:268-271) + `#stop` (:273-303); coupled drains: `#queueSend` :459-467.
**Signature:** public `stop(): Promise<void>` (memoized); private async `#stop(): Promise<void>`.
**Data Shape:** One memoized `#stopPromise` makes stop idempotent and single-flight; a local `cleanupError` accumulates via `??=` so only the FIRST cleanup failure survives.

### Decisive source
```ts
stop(): Promise<void> {
  if (!this.#stopPromise) this.#stopPromise = this.#stop();
  return this.#stopPromise;                    // concurrent callers share one run
}

async #stop(): Promise<void> {
  this.#stopped = true;                        // synchronous gate FIRST
  let cleanupError: Error | undefined;
  const recorder = this.#recorder; this.#recorder = undefined;
  if (recorder) { try { recorder.stop(); } catch (cause) { cleanupError = errorFrom(cause); } }
  await this.#sendChain;                       // drain ordered sends before closing
  const transport = this.#transport; this.#transport = undefined;
  if (transport) {
    try { await transport.send(buildSessionClose()); } catch (cause) { cleanupError ??= errorFrom(cause); }
    try { await transport.close(); }           catch (cause) { cleanupError ??= errorFrom(cause); }
  }
  if (cleanupError) this.#emitPhaseSafely("error");
  this.#emitTerminal(this.#failure ?? cleanupError);
}
```

**Flow:** flag stopped synchronously (every guard in the class checks it) → stop recorder first so no new samples arrive → await the send chain so already-queued delegation context still goes out → send `session.close` → close transport → surface phase `"error"` only if cleanup itself failed → terminal outcome prefers the latched runtime failure over incidental cleanup noise.
**Invariant:** Recorder-before-transport (no pushes into a closing socket), drain-before-close (queued messages are delivered or their send fails visibly — never silently dropped by an early `close()`), first-cleanup-error preservation via `??=`, exactly one `#stop` body ever runs, and a clean stop emits `onTerminal(undefined)` once.
**Probe:** `tests/live-controller.test.ts` (:132-135 after `controller.stop()`: last send was `{type:"session.close"}` AND call order ends `["send:session.close","close"]`; :135 terminal fired exactly once).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-better-openai", query: "stop stopPromise buildSessionClose sendChain drain", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the five-step order (flag → recorder → drain → protocol-close → transport-close) with single-flight memoization and `??=` first-error preservation. Adapt the protocol close frame to your wire format. Omit the LiveTransport interface specifics. Caveat: no upstream test exercises recorder.stop() throwing during teardown — source-pinned only.
