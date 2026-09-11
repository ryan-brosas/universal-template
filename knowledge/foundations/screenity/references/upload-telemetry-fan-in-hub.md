<!-- capsule-v2 -->
# Upload telemetry fan-in hub — what does the single telemetry entry point guarantee to its 26 callers?

**Source:** screenity GPL-3.0 `master@e10e375fafa1680de99ca6db36536dd4a1f4f7d4`; Codebase Memory `screenity`. **Question:** When every lifecycle hook (start, stall, offline, gap-resend, finalize, unload) emits diagnostics through one function, which defaults must it stamp and which events must it refuse to network-send?

## Fan-in enrichment + store-always / network-selective split
**Path/Symbol:** `src/pages/CloudRecorder/CloudRecorder.jsx:emitUploadTelemetry` (:1013-1044); callers census via trace (26: startRecording, stopRecording, onStall, onOffline, onOnline, onDataAvailable, checkMaxMemory, resendUploadGap, sweepStalledTracks, finalizeRecorderSession, clearStaleUploadJournals, emitAbandonedOnUnloadOnce, onHide, logForensicEvent, notePausedDrop, exportLocalRecovery, initializeUploaders, onUploaderTelemetry, scheduleCameraSilenceCheck, startStream, buildAudioBlobFromDurableStore, ensure*ChunkStoreReady ×3, emitRecordingOutcome).
**Signature:** `emitUploadTelemetry(event: string, payload = {}) => Promise<void>`.
**Data Shape:** builds `eventPayload` = fixed defaults (ids, runtime context, uploaderType) then `...payload` spread LAST so callers override anything; persists via BG relay always; network-sends unless suppressed.

### Decisive source
```js
const emitUploadTelemetry = async (event, payload = {}) => {
  const runtime = await ensureTelemetryRuntimeContext();
  const screenSceneId = screenUploader.current?.getMeta?.()?.sceneId || null;
  const cameraSceneId = cameraUploader.current?.getMeta?.()?.sceneId || null;
  const eventPayload = {
    event, ts: Date.now(),
    recordingSessionId: payload.recordingSessionId || recorderSession.current?.id || recordingSessionId.current || null,
    projectId: payload.projectId || recorderSession.current?.projectId || null,
    sceneId: payload.sceneId || screenSceneId || cameraSceneId || null,
    mediaId: payload.mediaId || null,
    bunnyVideoId: payload.bunnyVideoId || null,
    trackType: payload.trackType || null,
    uploaderType: payload.uploaderType || "cloud_recorder",
    extensionVersion: runtime.extensionVersion || resolveExtVersion(),
    browserVersion: runtime.browserVersion, platform: runtime.platform, arch: runtime.arch, os: runtime.os,
    ...payload,
  };
  await appendUploadTelemetryEvent(eventPayload);
  if (event !== "upload_progress") {
    void sendUploadTelemetryNetwork(eventPayload);
  }
};
```

**Flow:** resolve cached runtime context once → stamp id fallback ladders (session id: explicit payload → live session → module ref; scene id: payload → screen-uploader meta → camera-uploader meta) → caller payload wins via last spread → ALWAYS append to the durable BG store → network-send fire-and-forget (`void`) for everything except `upload_progress`.
**Invariant:** (1) persistence is unconditional — the store is the crash-forensics record; only the *network* copy is rate-managed; (2) `upload_progress` must never hit the network path or per-chunk progress floods the endpoint; (3) caller overrides must beat hub defaults, so the spread order can never be inverted; (4) network send is never awaited by callers (telemetry cannot delay recording).
**Probe:** no upstream tests exist at pin. Deterministic anchors: grep CloudRecorder.jsx for `...payload,` as the final key of the eventPayload literal (:1037) and `if (event !== "upload_progress")` (:1041). Byte-exact at HEAD.

## Get live surrounding code
**Retrieve:**
```
search_graph(project="screenity", name_pattern="emitUploadTelemetry")
→ observed: 1 row, lines 1013-1044, in=26 out=4 (exact match at pin)
get_code_snippet(project="screenity", qualified_name="screenity.src.pages.CloudRecorder.CloudRecorder.emitUploadTelemetry")
→ observed: served source byte-identical to checkout :1013-1044
```

## Verdict
Adopt the hub shape: one enrichment point with documented fallback ladders, store-always/network-filtered fan-out, caller-wins spreads. Adapt the runtime-context fields and the upload_progress carve-out list (add your own high-frequency types). Omit Screenity's uploader-meta scene resolution if your host has no dual track uploaders.
