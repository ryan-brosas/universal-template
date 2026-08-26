<!-- capsule-v2 -->
# Realtime session skeleton — how does an experimental browser voice session bootstrap and route events?

**Source:** Vercel AI SDK Apache-2.0 `main@9d9a73f1551f...`; Codebase Memory `ai`. **Question:** How does `AbstractRealtimeSession` wire token fetch, audio contexts, transport, and the reducer into one lifecycle?

## Token-endpoint bootstrap + reducer-mediated state
**Path/Symbol:** `packages/ai/src/realtime/realtime-session.ts` — `AbstractRealtimeSession` (:34), constructor wiring (:63–102), `connect()` (:106–146), `applyState` diffing (:269–288), abstract `setState` (:58–61).
**Signature:** `connect(): Promise<void>`; `applyState(nextState: RealtimeState): void`; subclass implements only `setState<K>(key, value)`.
**Data Shape:** setup POST returns `{token, url, tools}`; sample rates: capture from `sessionConfig.inputAudioFormat.rate`, playback from `outputAudioFormat.rate`, both defaulting to the single `sampleRate ?? 24000`.

### Decisive source
```ts
const response = await fetch(this.api.token, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ sessionConfig: this.sessionConfig }),
});
if (!response.ok) throw new Error(`Failed to fetch realtime setup: ${response.status}`);
const { token, url, tools: toolDefinitions } = await response.json();
this.audio.ensurePlaybackContext();          // AudioContext BEFORE transport opens
this.transport.connect({ token, url,
  onOpen: () => { this.sendEvent({ type: 'session-update', config }); } });
```

**Flow:** connect sets status `connecting` → POST to the TOKEN URL (an app endpoint that mints credentials server-side) → playback AudioContext created first (autoplay policies require a user-gesture-era context), then WS connects → on open the FULL merged config (incl. tools from setup response) is sent as `session-update` → every server event flows through `RealtimeEventReducer.reduceServerEvent` producing `{state, effects}`; state lands via `applyState`, which calls the subclass's `setState` PER CHANGED KEY (status/messages/events/isCapturing/isPlaying) so React bindings re-render minimally → errors set status `error` AND forward to `onError`.
**Invariant:** The session is a STATE MACHINE owned by the reducer — the session class never mutates messages itself. `connect()` swallows its own failures into status+onError rather than rejecting (callers observe via state, not try/catch). The abstract-setState seam is what makes the core testable headlessly (`realtime-session.test.ts` no-ops it).
**Probe:** deterministic: `grep -n "ensurePlaybackContext()" packages/ai/src/realtime/realtime-session.ts` → `127:`; `grep -n "Failed to fetch realtime setup" packages/ai/src/realtime/realtime-session.ts` → `116:`; `grep -n "'session-update'" packages/ai/src/realtime/realtime-session.ts` → `133:`. Direct tests: `realtime-session.test.ts:75–151` with mocked transport/audio.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "AbstractRealtimeSession RealtimeEventReducer reduceServerEvent", limit: 10, fields: ["signature","name","file"] });
// verified live @9d9a73f: rank#1 reduceServerEvent :115-250, then constructor/connect :63-146
```

## Verdict
Adopt the token-endpoint bootstrap, context-before-socket ordering, and per-key state diffing; adapt the event vocabulary to your realtime provider's protocol (v4 model adapter in `packages/provider/src/realtime-model/`); omit nothing — direct message mutation in a subclass breaks the reducer's event-sourced invariants.
