<!-- capsule-v2 -->
# Realtime hook store — how does an audio session object become React state with bounded event history and identity-keyed recreation?

**Source:** Vercel AI SDK Apache-2.0 `main@d25cae2722bfaed94c56d992c6df399a736db7a9`; Codebase Memory `ai`. **Question:** How does a realtime (speech-to-speech) session expose per-field subscriptions without a state library?

## experimental_useRealtime + RealtimeStore
**Path/Symbol:** `packages/react/src/use-realtime.ts:RealtimeStore` (:45-127), `useRealtime` (:151-244).
**Signature:** `class RealtimeStore extends AbstractRealtimeSession` overriding `setState(key, value)`, `pushMessage`, `updateMessages(updater)`, `pushEvent`; hook returns bound methods (`connect/disconnect/sendTextMessage/sendAudio/commitAudio/requestResponse/cancelResponse/startAudioCapture...`) plus 5 subscribed fields.
**Data Shape:** `state = {status, messages, events, isCapturing, isPlaying}` replaced IMMUTABLY on every change; per-field callback Sets (`callbacks[key]`); store recreation key = `{model, token, sessionConfig, sampleRate, maxEvents}` (BY-IDENTITY comparison of sessionConfig).

### Decisive source
```ts
// immutable replacement — new state OBJECT per update so external-store
// snapshots change identity:
protected setState(key, value) { this.state = { ...this.state, [key]: value }; this.callbacks[key].forEach(cb => cb()); }
// events are RING-BOUNDED at the tail:
protected pushEvent(event) {
  const nextEvents = [...this.state.events, event];
  this.state = { ...this.state, events: nextEvents.length > this.maxEvents ? nextEvents.slice(-this.maxEvents) : nextEvents };
  this.callbacks.events.forEach(cb => cb());
}
// recreate the store ONLY when connection-shaping options change by IDENTITY;
// callbacks still read through refs so they can never go stale:
if (realtimeEntry == null || shouldCreateRealtimeStore(realtimeEntry.key, options)) {
  realtimeEntry = { store: new RealtimeStore({...options,
    onToolCall: (...a) => callbacksRef.current.onToolCall?.(...a), /* same for onEvent/onError */ }),
    key: getRealtimeStoreKey(options) };
} else { realtimeEntry.key = getRealtimeStoreKey(options); }
```

**Flow:** render → refresh callbacksRef → decide store recreation via 5-field key (model/token/sessionConfig-by-reference/sampleRate/maxEvents) → five independent `useSyncExternalStore` subscriptions (one per field) read getters → unmount effect calls `rt.dispose()`. Session lifecycle (WebAudio capture/playback, server events, tool outputs keyed by callId) lives in AbstractRealtimeSession (experimental, `ai` package); the hook is purely the React binding.
**Invariant:** field updates replace the whole state object but notify ONLY that field's subscribers — a naive single-callback store re-renders audio UI on every transcript delta. Event history is capped at `maxEvents` (memory bound against hours-long sessions). Store recreation on config change DISCARDS session state deliberately; stale-callback safety comes from ref indirection, not from keeping one store forever.
**Probe:** `packages/react/src/use-realtime.test.tsx` (store semantics + subscription behavior).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "RealtimeStore useRealtime pushEvent maxEvents subscribe", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt immutable-state-replacement + per-field subscriber sets + tail-bounded event ring + identity-keyed recreation. Adapt the option key set to your session parameters. Omit the concrete WebAudio plumbing unless porting the full realtime stack (lives in `AbstractRealtimeSession`, separately minable).
