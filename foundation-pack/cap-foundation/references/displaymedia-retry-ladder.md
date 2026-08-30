<!-- capsule-v2 -->
# displaymedia-retry-ladder — How do you call getDisplayMedia so surface preferences and system audio degrade gracefully without ever swallowing a user cancellation?

**Source:** cap AGPL-3.0 `main@0ce9e67516b14449c4263c0b173c85c40f30421b`; Codebase Memory `ext-cap`. **Question:** What is the exact attempt order (preferred → no-preferences → no-audio), which errors trigger each fallback, and what fires once per degradation?

## preferred → base (no prefs) → noAudio; only Overconstrained/NotSupported/InvalidAccess/TypeError retry; NotAllowedError|AbortError rethrow untouched; onSystemAudioFallback fires ONCE per fallback
**Path/Symbol:** `packages/recorder-core/src/capture-streams.ts:72-209` (`acquireDisplayStream`), error classifiers `recorder-utils.ts:255-272` (`isUserCancellationError`, `shouldRetryDisplayMediaWithoutPreferences`), mixer `:229-287` (`createAudioMixer`).
**Signature:** `acquireDisplayStream({mode?, systemAudioEnabled, onSystemAudioFallback?}): Promise<MediaStream>`.
**Data Shape:** System-audio track constraints disable echoCancellation/autoGainControl/noiseSuppression; `displaySurface: desiredSurface ?? undefined` — undefined members are treated as ABSENT by the constraint algorithm, so the generic path adds no preference.

### Decisive source
```ts
} catch (audioRetryError) {
    if (systemAudioEnabled && shouldRetryDisplayMediaWithoutPreferences(audioRetryError)) {
        console.warn("System audio not supported, retrying without audio", audioRetryError);
        onSystemAudioFallback?.();
        videoStream = await navigator.mediaDevices.getDisplayMedia(noAudioDisplayRequest);
    } else { throw audioRetryError; }
}
```

**Flow:** With a detected mode, first try `preferredDisplayRequest` (mode-specific options merged UNDER explicit video/audio keys). Failure classification: user cancellation rethrows immediately everywhere; retryable classes descend the ladder — first without mode preferences, then without system audio (firing the fallback callback). When the no-audio PREFERRED retry also fails, the ORIGINAL display error is rethrown (the first error is the informative one). Without any mode, one base attempt with the same audio-only fallback. The mixed output rides an AudioContext graph: sources → DynamicsCompressor limiter (-3dB threshold, ratio 20, 2ms attack) → MediaStreamDestination whose OUTPUT TRACK IDENTITY NEVER CHANGES, so setMicStream can hot-swap mid-recording with no MediaRecorder gap.
**Invariant:** Cancellation must never be retried (it's the user closing the picker). Limiter destination identity stability is the contract enabling live mic swaps. Fallback callback fires exactly once per degradation event.
**Probe:** `packages/recorder-core/__tests__/capture-streams.test.ts` — `retries without preferences, then without audio, firing the fallback once` (:96), `rethrows user cancellation immediately with no retries` (:143), `connects the mic and swaps it live without changing the output stream` (:198).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-cap", query: "acquireDisplayStream createAudioMixer retry", limit: 10 });
```

## Verdict
Adopt the ladder + classifier pair and stable-destination mixer. Adapt constraint tables and limiter values to your product's audio chain.
