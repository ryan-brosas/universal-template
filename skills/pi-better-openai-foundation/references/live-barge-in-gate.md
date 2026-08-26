<!-- capsule-v2 -->
# Barge-in echo gate — how do you pipe microphone audio into a voice session without feeding back the assistant's own voice?

**Source:** pi-better-openai MIT `main@86814e9047996abba08e4c907e23286329196fe0`; Codebase Memory `pi-better-openai`. **Question:** What gating must run between raw mic samples and the transport's pushAudio to block echo while allowing interruption?

## Audio gate
**Path/Symbol:** `src/live/controller.ts:#handleMicrophoneAudio` (:364-394); thresholds `OUTPUT_ACTIVE_LEVEL=0.015`, `MIN_BARGE_IN_LEVEL=0.04`, `OUTPUT_ECHO_RATIO=0.65`, `DIGITAL_SILENCE_SAMPLE_LIMIT=32_000` (:13-16).
**Signature:** `(samples: Float32Array): void` fed by native capture at 16kHz; RMS level via exported `microphoneLevel(samples)` (:93-101).
**Data Shape:** Input sample blocks; internal output level from the peer's `onOutputLevel` callback clamped to [0,1].

### Decisive source
```ts
const outputActive = this.#outputLevel > OUTPUT_ACTIVE_LEVEL;
const echoThreshold = Math.max(MIN_BARGE_IN_LEVEL, this.#outputLevel * OUTPUT_ECHO_RATIO);
if (outputActive && this.#inputLevel < echoThreshold) return;   // echo of own voice
try { this.#transport.pushAudio(samples); } catch (cause) { this.#reportFailure(...); }
```
Digital-silence watchdog (:366-383): before ANY non-zero sample arrives, count total silent samples; past 32k (≈2s @16kHz) report "Microphone input contains only digital silence." with platform-aware permission hint and STOP processing — distinguishes muted hardware from a quiet room.

**Flow:** samples → (once) silence watchdog → RMS input level → emit levels → if assistant audio active AND input below max(floor, 65%·output): drop as echo → else push to transport.
**Invariant:** The floor (`MIN_BARGE_IN_LEVEL`) guarantees a genuinely loud interrupt ALWAYS passes even while output is loud — barge-in stays possible; quiet-samples-during-output are classified echo and dropped; push failures surface as session failure, never silently vanish.
**Probe:** `tests/live-controller.test.ts` (:204 digital-silence failure message; echo/barge-in threshold behavior pinned through controller integration — direct threshold matrix spec absent at this pin, caveat).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-better-openai", query: "microphoneLevel handleMicrophoneAudio OUTPUT_ECHO_RATIO", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the three-part contract: ratio-with-floor echo classification, digital-silence watchdog with actionable hint, clamp+RMS level metering. Adapt thresholds to your sample rate/capture chain. Omit the localterm-specific hint branch.
