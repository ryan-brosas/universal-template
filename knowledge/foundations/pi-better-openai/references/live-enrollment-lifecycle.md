<!-- capsule-v2 -->
# Enrollment/park lifecycle — how does an always-available voice command cost zero open connections while idle?

**Source:** pi-better-openai MIT `main@86814e9047996abba08e4c907e23286329196fe0`; Codebase Memory `pi-better-openai`. **Question:** How should `/live` separate ENROLLMENT (queue membership) from ACTIVATION (realtime session) so arbiter grants can create and destroy sessions repeatedly?

## Enrollment split
**Path/Symbol:** `src/live/index.ts:registerOpenAILive` (:99-349); comment block :34-43 states the design; `parkSession` :167-174, `activateSession` :176-212, tick interval :255-262, focus debounce :264-281.
**Signature:** `registerOpenAILive(pi, getConfig, dependencies?): { isActive(), stop() }` with injectable `createSession/createArbiter/probeFocusReporting/attachFocusReporting/tickMs`.
**Data Shape:** One `ActiveLiveRun` closure owning visualizer + optional session + optional arbiter; enrollment outlives sessions.

### Decisive source
```ts
const parkSession = () => {           // floor LOST: stop mic+WebRTC, stay enrolled
  const current = session; session = undefined; sessionParked = true;
  visualizer.setPhase("standby"); visualizer.setTranscript(undefined);
  if (current) void current.stop().catch(() => undefined);
};
const activateSession = () => {       // floor GRANTED: build session lazily
  if (completed || session) return;
  ...
  setImmediate(() => { if (session !== created) return;
    void created.start().catch((cause) => finishUi({ error })); });
};
onActivated: (cause) => { if (cause !== "focus") notifyUnfocused(terminalHandle, enrolled.label); activateSession(); },
onDeactivated: parkSession,
```
Focus-in debounce (`LIVE_FOCUS_SETTLE_MS=400`) prevents window-manager flicker from flapping floor ownership (:270-280); ticks are try/caught so one failing tick never tears down enrollment (:255-261); `dispose()` order = clear timers → dispose focus → `arbiter.leave()` → stop session (:214-224); `settling` promise serializes overlapping toggles (:114-124, :291-298); OSC 9 toast fires when the mic goes hot in an unfocused window (:63-76).

**Flow:** `/live` → TUI-only guard + config gate → open custom UI (visualizer in standby) → probe focus support → enroll arbiter (policy focus|fifo) → join + tick loop → on grant: activate (create+start session deferred via setImmediate); on loss: park (session destroyed, enrollment persists).
**Invariant:** Only the floor holder EVER runs a realtime session — a dozen enrolled windows cost zero connections at standby; session identity is re-checked inside the setImmediate callback so a park-race can't start a stale session.
**Probe:** `tests/live-registration.test.ts` (:203 activation-on-grant + cleanup-on-close, :316 unfocused-notification wiring, :175 event ordering message_end→agent_settled→session_shutdown).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-better-openai", query: "registerOpenAILive parkSession activateSession", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the enroll-park-activate separation with deferred-start race check and debounced focus edges. Adapt dependency injection surface and notification channel. Omit the pi ExtensionAPI glue.
