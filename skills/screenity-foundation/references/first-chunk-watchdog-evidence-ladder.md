<!-- capsule-v2 -->
# First-chunk watchdog evidence ladder — when may a background watchdog kill a "stuck" recording?

**Source:** screenity GPL-3.0 `master@e10e375fafa1680de99ca6db36536dd4a1f4f7d4`; Codebase Memory `screenity`. **Question:** A BG alarm fires because no chunk ever landed — which observable signals justify rearming vs failing, and when is the failure a device-defect sticky-disable?

## Snapshot-bounded rearm ladder
**Path/Symbol:** `src/pages/Background/alarms/handleAlarm.js:246-407` (`FIRST_CHUNK_WATCHDOG_ALARM` branch of `handleAlarm`).
**Signature:** `handleAlarm(alarm: {name: string}): Promise<void>` (branch keyed on `alarm.name`).
**Data Shape:** snapshot from the recorder tab via message with a 1500ms race cap; fields consumed: `counts.{saved,pendingBytes,hasChunks}`, `progress.{frameCount,framesFromMSTP}`, `flags.{paused,isStarting}`, `stream.videoTrack.{readyState,muted}`, persisted `firstChunkWatchdogState.rearms`.

### Decisive source
```js
      // Fail on missing frames, not a missing chunk. First-chunk latency is
      // unbounded (cold start, keyframe cadence, slow disk); frame arrival
      // isn't, so zero frames means capture is dead at 8s or at 80s. ...
      const bytesExist =
        Boolean(counts) && (Number(counts.saved) > 0 || Number(counts.pendingBytes) > 0 || counts.hasChunks === true);
      const framesArriving = Boolean(progress) && (Number(progress.frameCount) > 0 || Number(progress.framesFromMSTP) > 0);
```
Rearm order: bytes-exist → clear+return; paused → rearm (ignores cap); no snapshot within 1500ms → rearm ("a recorder too busy to answer in 1500ms isn't a dead capture"); still-starting → rearm; frames-arriving-no-chunk-yet → rearm; MediaRecorder (no frame counter) live+unmuted track + state "recording" → rearm.
Final triage:
```js
      if (vt && vt.readyState === "live" && vt.muted === true) {
        // Capture track is live but muted: ... That
        // is not an encoder defect, so don't disable WebCodecs and don't fail
        // the recording. ...
      } else {
          const realEncoderDefect =
            Boolean(vt) && vt.readyState === "live" && vt.muted === false;
          if (fastRecorderInUse && realEncoderDefect) {
            await markFastRecorderFailure("webcodecs-no-first-chunk", { ... });
          }
        // handleRecordingError (not sendMessageRecord) so the editor gets notified
        await handleRecordingError({ error: "stream-error", ..., errorCode: "no-first-chunk" });
```

**Flow:** alarm fires → bounded snapshot (1500ms) → persist `lastFirstChunkWatchdog` evidence → short-circuit success if any bytes reached disk (the cancel message was lost) → walk rearm reasons under a max-rearms cap → muted-track starvation logs and waits → only live ∧ unmuted ∧ no-chunk counts as the genuine silent-encoder defect (sticky-disable) while an ended track / absent snapshot fails the take WITHOUT disabling the fast path.
**Invariant:** first-chunk latency alone is never a failure signal; every non-terminal outcome must consume a rearm slot (bounded retries); ambiguous evidence fails the take but leaves the fast path enabled; only unambiguous encoder-defect evidence writes the sticky ban.
**Probe:** deterministic anchors: grep handleAlarm.js for `Fail on missing frames, not a missing chunk` (:292-294), `is not an encoder defect, so don't disable WebCodecs` (:373-374), `realEncoderDefect` (:383), `A long pause must never age into a failure` (:322-323). Byte-exact at HEAD.

## Get live surrounding code
**Retrieve:**
```
trace_path(project="screenity", function_name="markFastRecorderFailure", direction="inbound")
→ observed handleAlarm among 19 callers — the watchdog is one of two BG writers of the sticky ban,
  and its detail-less report is the one the transient-clear rule in markFastRecorderFailure overrides.
```

## Verdict
Adopt the evidence taxonomy (bytes > pause > responsiveness > starting > frames > MR-heuristic > muted-starvation > defect) and the fail-vs-disable split for ambiguity. Adapt snapshot field names and rearm caps to your recorder's telemetry. Omit Chrome alarms scheduling details.
