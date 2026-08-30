<!-- capsule-v2 -->
# Derived audio phase machine — how does the UI phase stay truthful when mute, delegation, and peer audio all change asynchronously?

**Source:** pi-better-openai MIT `main@1188f985389328cff660b6bdbe52f38fdb826c70`; Codebase Memory `pi-better-openai`. **Question:** Instead of setting UI states at every call site, how do you derive one phase (`standby|connecting|listening|working|speaking|muted|error`) from live audio/delegation state with correct priority and sticky behavior?

## Phase derivation
**Path/Symbol:** `src/live/controller.ts:#refreshAudioPhase` (:469-475), `#emitPhase` (:477-485), `#emitPhaseSafely` (:487-494); stickiness gate `#handleOutputLevel` :358-362; `LivePhase` union :28-35.
**Signature:** private `#refreshAudioPhase(): void`; private `#emitPhase(phase: LivePhase, force = false): void`.
**Data Shape:** Inputs: `#muted`, `#activeDelegationId`, `#outputLevel` (clamped [0,1]); threshold shared with the barge-in gate: `OUTPUT_ACTIVE_LEVEL = 0.015`.

### Decisive source
```ts
#refreshAudioPhase(): void {
  if (this.#stopped) return;
  if (this.#muted)                   this.#emitPhase("muted");
  else if (this.#activeDelegationId) this.#emitPhase("working");
  else if (this.#outputLevel > OUTPUT_ACTIVE_LEVEL) this.#emitPhase("speaking");
  else                               this.#emitPhase("listening");
}

#handleOutputLevel(level: number): void {
  this.#outputLevel = clampLevel(level);
  this.#emitLevels();
  if (!this.#activeDelegationId) this.#refreshAudioPhase();   // "working" stays sticky
}
```

**Flow:** priority ladder muted > working > speaking > listening recomputed on every input change — mute toggle (:222-235), output level from the peer, delegation create (`#handleDelegation` forces `"working"` :350) and settle (:265). Two event-driven exceptions bypass the ladder: `start()` forces `"connecting"` via `force=true` (:178) and `session.started` sets `"listening"` directly (:316-318). Emission dedupes on the current phase unless forced; terminal/error paths use `#emitPhaseSafely`, which skips dedup AND never feeds back into `#reportFailure` (no recursion at shutdown).
**Invariant:** The phase is a pure function of state, never stored by callers — so any missed event self-heals on the next refresh; while a delegation is active the working phase is sticky against speaker-audio flicker; emit callbacks are exception-contained in all three variants but only the forced/safely forms may bypass or drop dedup. `"error"` is reachable ONLY through the failure latch / cleanup path, never from the ladder.
**Probe:** `tests/live-controller.test.ts` (:83 `expect(phases).toContain("working")` after a `delegation.created` event). Caveat: no upstream test pins the full priority ladder itself (mute-over-working over speaking etc.) — derived-ladder claims are source-pinned.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-better-openai", query: "refreshAudioPhase emitPhase emitPhaseSafely OUTPUT_ACTIVE_LEVEL", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt derive-don't-store phase with an explicit priority ladder, a sticky-state gate during long operations, and the dedup/force/safe emission trio. Adapt phase names and your own sticky conditions. Omit the visualizer's standby rendering (registration-layer concern, see live-enrollment-lifecycle).
