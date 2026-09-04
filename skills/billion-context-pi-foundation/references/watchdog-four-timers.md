<!-- capsule-v2 -->
# Five-timer child watchdog — how is a hung delegate guaranteed to die, during AND after its run, without ever pinning the host process?

**Source:** billion-context-pi (MIT) `master@6a88c5565355`; Codebase Memory project `mnt-hdd-utopia-inspo-billion-context-pi`. **Question:** Which timer set guarantees termination of a stuck child — and of a hung teardown after the run is already over?

## Idle + hard + EOF-grace + TERM→KILL grace DURING the run; settled-grace AFTER it
**Path/Symbol:** `src/delegate-watchdog.ts` (125 lines, whole-file read at pin): `attachWatchdogs` (:43-125), `killByWatchdog` (:62-79), `settledGrace` (:81-90, see watchdog-settled-grace capsule for the full contract), `poke` (:92-96), `dispose` (:120-123). Re-anchored at 6a88c556 — pass-4 anchors (:32-100 attach) drifted.
**Signature:** `attachWatchdogs(child: {kill(signal), stdout: Readable|null}, hooks: {isSettled, onKill, onEofGrace}, opts: {eofGraceMs, idleMs, timeoutMs, killGraceMs}) -> {poke, dispose, settledGrace(graceMs, _killGraceMs, reason)}`. Attached ONLY on the async spawn path (`delegate-tool.ts`).
**Data Shape:** every timer `.unref?.()`; poke = clear+re-arm on every stdout data chunk; settledGrace adds one optional timer cleared on dispose.
### Decisive source
```ts
// Module docstring :37-42 states the core problem directly:
// a stuck child holds its stdout fd open, so stdout EOF never fires.
// A hard timeout alone fires too late; EOF alone never fires. Hence FIVE timers:
//  1. idle        — poke() clears+re-arms on EVERY stdout data chunk (:92-96);
//                   "no output for Xm" → killByWatchdog
//  2. hard        — armed once at attach (:99-100)
//  3. eof         — child.stdout.once("end") :115 → if not exited within
//                   eofGraceMs → hooks.onEofGrace() + SIGTERM anyway (:102-114)
//  4. killGrace   — SIGTERM then SIGKILL after killGraceMs (:70-78)
//  5. settledGrace— agent_settled received but process alive past graceMs →
//                   killByWatchdog (:81-90; teardown hang, e.g. a provider
//                   call not returning; normal exits are ms-level)
```

**Flow:** output keeps re-arming the idle timer; silence fires it. On stdout end, the EOF-grace window covers "output ended but process did not exit" — finalize afterwards treats delivered output as success even without an exit code (`effectiveCode` fallback in delegate-tool.ts finalize). Escalation re-checks settlement TWICE before each signal (`killByWatchdog` checks `isSettled()` at entry AND inside the killGrace timer; the eof timer re-checks before firing) — a run that settles during a grace window is not killed. After settle, the fifth timer bounds teardown: pi emits agent_settled exactly once in `_runAgentPrompt`'s finally ("the process should exit within milliseconds"); if it's still alive ~10s later (symmetric with eofGraceMs), the watchdog kills it. `settledGrace` clears the timer reference BEFORE killing so a re-entrant kill or subsequent call sees no pending timer (:84-87). This closes the post-run gap the original four timers left open — they only protect DURING a run.
**Invariant:** (1) idle-timeout is the PRIMARY defense because a hung child defeats EOF by holding the fd open — porters who lead with EOF detection will hang forever. (2) `isSettled` must be consulted immediately before EVERY kill signal, not once at attach. (3) poke clears before re-arming so overlapping data chunks never multiply idle timers. (4) dispose clears all five timers AND removes the `end` listener (:120-123) — no leaks on long-lived hosts; settledGrace's clear-before-kill ordering prevents re-entrant kills. (5) Kill reasons surface to the model as `(timed out: no output for 5m)` in completion headers.
**Probe:** EXECUTED this pass via repo runner `npm test`: 414/414 GREEN at pin 6a88c556, including `tests/watchdog.test.ts` — idle SIGTERM (:61), SIGKILL escalation when TERM ignored (:70), continuous output never triggers via poke reset (:77), EOF-grace force-finalize (:87), hard limit regardless of output (:95), dispose stops all (:103), settled runs never killed or grace-finalized (:112), PLUS the settledGrace pins: kills on hang (:120), escalates (:130), no-op when already settled (:138), idempotent arming (:146), dispose clears pending (:157), settle-before-fire stops kill (:165).
**Coverage:** whole-file source read confirms all anchors; tests/watchdog.test.ts exists and passes at this pin.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-billion-context-pi", query: "attachWatchdogs poke eofTimer killGrace settledGrace", limit: 10 });
```
EXECUTED: resolves `src.delegate-watchdog.attachWatchdogs` :43-125, `killByWatchdog` :62-79, `settledGrace` :81-90, `poke` :92-96, `dispose` :120-123.

## Verdict
Adopt all five timers and both pre-kill settled checks — this is a complete, test-pinned termination contract covering both a stuck child and a hung post-settle teardown. Adapt durations to your workload. Omit nothing from dispose(); listener leakage here accumulates across sessions on long-lived hosts.
