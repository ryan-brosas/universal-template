<!-- capsule-v2 -->
# Start race recheck ladder — how do you bring up mic capture plus a connecting transport without racing a concurrent stop?

**Source:** pi-better-openai MIT `main@1188f985389328cff660b6bdbe52f38fdb826c70`; Codebase Memory `pi-better-openai`. **Question:** `start()` awaits transport negotiation, and the user can hit stop at any moment — where must the stopped-state be rechecked so no orphan recorder or half-open session leaks?

## Start ladder
**Path/Symbol:** `src/live/controller.ts:start` (:172-220); race guards at :173-176 (pre-checks), :204-207 (post-capture), :210-211 (post-connect); failure tail :214-219.
**Signature:** `async start(): Promise<void>` — idempotent via `#started`, throws the latched `#failure` if already stopped.
**Data Shape:** Options carry injectable `createTransport`/`createAudioCapture` factories plus `native`; default audio path is `new native.AudioCapture(16_000, onAudio)`.

### Decisive source
```ts
if (this.#stopped) throw this.#failure ?? new Error("This live session has already stopped.");
if (this.#started) return;                     // idempotent second call
this.#started = true;
this.#emitPhase("connecting", true);
...
const recorder = this.#createAudioCapture ? ... : new native.AudioCapture(16_000, onAudio);
if (this.#stopped) {                           // stop() ran while capture was created
  recorder.stop();                             // release the orphan immediately
  throw this.#failure ?? new Error("The live session stopped while recording began.");
}
this.#recorder = recorder;
await transport.connect();                     // ← arbitrary async gap
if (this.#stopped) throw this.#failure ?? new Error("The live session stopped while connecting.");
transport.setMuted(this.#muted);
this.#refreshAudioPhase();
```

**Flow:** guard → mark started → force `"connecting"` phase → resolve native bindings (injected or `loadLiveNative()`) → build transport through the factory with guarded callbacks (`onEvent`/`onOutputLevel` both wrapped in `#guardEvent`) → create audio capture → **recheck stopped** → store recorder → await connect → **recheck stopped again** → push current mute state into the transport → derive first real phase. Any throw: `errorFrom` → `#reportFailure` → `await this.stop()` → rethrow to the caller.
**Invariant:** Capture begins BEFORE negotiation completes (mic warms up during WebRTC connect) but every await is followed by a synchronous stopped-recheck that releases the just-created resource before throwing; a start that loses the race never leaves an un-stopped recorder or resolves into a live session; the thrown error is the latched failure when one exists, so callers see the cause rather than a generic "already stopped".
**Probe:** `tests/live-controller.test.ts` (:138-170 — `createAudioCapture` observed called once BEFORE the manually-resolved `connect` promise settles, proving capture-during-negotiation). Caveat: the two mid-ladder recheck branches (:204-207/:210-211) have no upstream test — source-pinned only.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-better-openai", query: "start createAudioCapture connect stopped recheck", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt idempotent-start + recheck-after-every-await + orphan-release-before-throw. Adapt factory injection surface to your DI style. Omit Codex credential plumbing (`getCredentials` passes straight through). Caveat recorded above for untested recheck branches.
