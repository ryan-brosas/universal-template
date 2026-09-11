<!-- capsule-v2 -->
# Once-only failure→terminal latch — how do you guarantee a session reports exactly one terminal outcome no matter how many subsystems fail?

**Source:** pi-better-openai MIT `main@1188f985389328cff660b6bdbe52f38fdb826c70`; Codebase Memory `pi-better-openai`. **Question:** When mic capture, transport sends, callbacks, and teardown can each throw, what latching discipline keeps the UI to a single authoritative failure while later errors still get recorded?

## Failure ladder
**Path/Symbol:** `src/live/controller.ts:#reportFailure` (:513-519), `#emitTerminal` (:521-529), `#failure`/`#terminalEmitted` fields (:132-133); consumer `errorFrom` (:84-86).
**Signature:** private `#reportFailure(error: Error): void`; private `#emitTerminal(error?: Error): void`.
**Data Shape:** One latched `Error | undefined` (`#failure`) plus a one-shot boolean (`#terminalEmitted`); every caller converts unknown throws via `errorFrom` so the latch always holds a real `Error`.

### Decisive source
```ts
#reportFailure(error: Error): void {
  if (this.#terminalEmitted) return;      // first failure wins; later ones dropped
  this.#failure = error;
  this.#emitPhaseSafely("error");         // phase flip must not recurse into reporting
  this.#emitTerminal(error);              // exactly-once UI boundary
  void this.stop();                       // failure implies shutdown
}

#emitTerminal(error?: Error): void {
  if (this.#terminalEmitted) return;
  this.#terminalEmitted = true;
  try { this.#callbacks.onTerminal(error); } catch {
    // Nothing remains above the terminal callback to receive its error.
  }
}
```

**Flow:** any guarded layer (audio callback, event dispatch, send chain, delegation hook) converts its cause → `#reportFailure` → latch error + emit `"error"` phase → fire `onTerminal` once → async `stop()`. Clean shutdowns reach `onTerminal(undefined)` through `#stop`'s final line (:302). After the latch, every subsequent failure is a silent no-op and `start()` re-throws the latched `#failure` instead of "already stopped" (:174).
**Invariant:** `onTerminal` fires at most once per session with either the first failure or undefined — never both, never twice; callback errors from the terminal boundary itself are swallowed by design because nothing above remains to handle them; the latched error outlives cleanup so `stop()` can prefer real cause over incidental close noise (`#emitTerminal(this.#failure ?? cleanupError)` :302).
**Probe:** `tests/live-controller.test.ts` (:200-204 digital-silence failure fires terminal exactly once with an Error whose message contains "only digital silence"; :135 terminal called once after clean stop).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-better-openai", query: "reportFailure emitTerminal terminalEmitted", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the two-flag latch (first-error field + one-shot boolean) with failure-implies-stop and the swallow-at-terminal-boundary rule. Adapt where your UI boundary lives (promise rejection vs callback vs event). Omit the pi visualizer wiring. Caveat: no upstream test forces two competing failures to prove drop-after-latch — source-pinned only.
