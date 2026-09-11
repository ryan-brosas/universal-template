<!-- capsule-v2 -->
# Encoder round-trip support ladder — how do you detect the silent zero-output encoder that isConfigSupported vouches for?

**Source:** screenity GPL-3.0 `master@e10e375fafa1680de99ca6db36536dd4a1f4f7d4`; Codebase Memory `screenity`. **Question:** `VideoEncoder.isConfigSupported` says yes but Windows MFT emits a 28-byte header-only file — what probe actually proves an encoder produces output, and when may its failure be forgiven?

## Config ladder + real encode round-trip
**Path/Symbol:** `src/media/fastRecorderGate.ts:452-808` (`_probeFastRecorderSupportUncached`), `:232-320` (`verifyEncoderProducesOutput`), `:324-379` (`verifyAudioEncoderProducesOutput`).
**Signature:** `verifyEncoderProducesOutput(config: VideoEncoderConfig): Promise<{ok, reason?, chunks, ms}>`.
**Data Shape:** ladder iterates 2 sizes × 2 codecs × 4 hw modes × 6 knob-omission steps, first supported config wins; round-trip returns chunk count + wall-clock ms.

### Decisive source (the probe that catches zero-output)
```ts
// Push 4 synthetic frames through a real VideoEncoder to catch the
// "28-byte ftyp" zero-output failure isConfigSupported misses.
const PROBE_FRAME_COUNT = 4;
const PROBE_WALL_CLOCK_CAP_MS = 1500;
...
    // Wall-clock cap: a stressed encoder can drain for tens of seconds.
    // Classify on whatever landed.
    await Promise.race([encoder.flush(), new Promise((_, reject) => {
      flushTimer = setTimeout(() => { flushTimedOut = true; reject(new Error("flush-timeout")); },
        PROBE_WALL_CLOCK_CAP_MS);
    })]);
  } catch (err) {
    // If we timed out and at least one chunk landed, that's an OK
    // signal; encoder is producing output, just slow. ...
    if (!flushTimedOut || chunks === 0) { encoderError = ...; }
  }
...
  // Only zero-output is a firm fail; runtime watchdogs handle slow encoders.
  if (chunks === 0) return { ok: false, reason: "no-output", chunks, ms };
```

### Decisive source (retry + trust-window policy)
```ts
// Retry once on transient errors (VTDecoderXPC, NVIDIA, VAAPI all
// reject the first configure() after another encoder ran). "no-output"
// is a real HW bug and does NOT retry.
if (!encodeCheck.ok && encodeCheck.reason === "error") {
  await new Promise((r) => setTimeout(r, 200));
  const retry = await verifyEncoderProducesOutput(...); ...
}
...
// Trust a clean probe from the last 7 days when only transient errors
// failed: in-session MediaRecorder swap covers the WebCodecs miss.
const onlyTransientReasons =
  reasons.every((r) => r === "video-encode-error" || r === "audio-encode-error");
```
Codec candidates are deliberately narrow:
```ts
// High L4.2 and Baseline L4.0. Main (avc1.4D...) excluded for the
// Windows MFT silent-no-output bug (see WebCodecsRecorder).
const codecCandidates = ["avc1.64002A", "avc1.42E028"];
```

**Flow:** capability flags → isConfigSupported ladder → MP4 playable-codec check (`canPlayType`, MSE) with Linux codec-gap tagging → WebM/VP9+Opus fallback when MP4 fails → real video round-trip (retry-once on error) → audio round-trip (non-blocking, tags separately) → transient-only failure overridden by ≤7-day clean stored probe → persist ok result to storage / failure to a separate key.
**Invariant:** timeout-with-chunks is OK (slow ≠ broken); zero-output is the only firm video fail and never retries; audio round-trip failure never blocks selection; the trust override requires matching UA AND gate version on the prior clean probe.
**Probe:** deterministic anchors: grep for `"28-byte ftyp" zero-output failure` (:228-229), `Only zero-output is a firm fail` (:317), `"no-output"\n  is a real HW bug and does NOT retry` (:706-707), `Trust a clean probe from the last 7 days` (:743). Byte-exact at HEAD.

## Get live surrounding code
**Retrieve:**
```
search_graph(project="screenity", name_pattern="^verify(Audio)?EncoderProducesOutput$", fields=["lines"])
→ observed 2 rows at :232-320 / :324-379 with out-degree 7 and 5 (config consumers inside the same module).
```

## Verdict
Adopt the round-trip probe, the error-vs-no-output retry asymmetry, and the transient trust window. Adapt codec sets and knob lists to your targets (keep excluding any codec family with known silent-output bugs). Omit the attempt-summary telemetry payload shape.
