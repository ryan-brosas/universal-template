<!-- capsule-v2 -->
# Crash recovery download-then-clear — how are durable chunks rescued after a process crash without risking the user's only copy?

**Source:** screenity GPL-3.0 `master@e10e375fafa1680de99ca6db36536dd4a1f4f7d4`; Codebase Memory `screenity`. **Question:** When a recorder tab crashed mid-session leaving durable chunks behind, what is the safe order of detect → export → destroy?

## Once-guarded backend-aware recovery that downloads BEFORE clearing
**Path/Symbol:** `src/pages/CloudRecorder/CloudRecorder.jsx:tryRecoverPreviousSession` (:3146-3290); mounted once via effect (:5798-5800).
**Signature:** `tryRecoverPreviousSession() => Promise<void>` (guarded by `recoveryAttempted.current`).
**Data Shape:** stored `recorderSession` with `storageBackends: {screen|audio|camera: "idb"|"opfs"}`, `opfsSessionId`, `status`, `id`; per-track durable chunk stores expose `length()/iterate()/clear()`.

### Decisive source
```js
const tryRecoverPreviousSession = useCallback(async () => {
  if (recoveryAttempted.current) return;
  recoveryAttempted.current = true;
  // Recovery reads from whatever backend the previous session wrote to.
  // Sessions before the OPFS migration have no storageBackends field; fall
  // back to IDB across the board, matching pre-migration behaviour.
  const prevBackends = storedSession?.storageBackends || { screen: "idb", audio: "idb", camera: "idb" };
  const recoveryScreenStore = openExistingChunksStore({ sessionId: prevOpfsSessionId, track: "screen", backend: prevBackends.screen || "idb" }).store;
  // ... same for camera/audio ...
  const isRecoverable = RECOVERABLE_SESSION_STATUSES.has(storedSession?.status);
  const hasDurableChunks = chunkCount > 0 || cameraChunkCount > 0 || audioChunkCount > 0;
  if (storedSession && isRecoverable && hasDurableChunks) {
    void emitUploadTelemetry("upload_recovery_available", { reason: "durable-chunks", /* counts */ });
    // per track: iterate -> sort by index -> createBlobFromChunks(..., "video/webm")
    await chrome.downloads.download({ url: objectUrl, filename: `Screenity-Recovered-${ts}.webm`, saveAs: false });
    // finally:
    // download() resolves before the blob fetch; delay revoke.
    setTimeout(() => { try { URL.revokeObjectURL(objectUrl); } catch {} }, 2000);
    // after ALL exports:
    await recoveryScreenStore.clear().catch(() => {});
    await recoveryAudioStore.clear().catch(() => {});
    await recoveryCameraStore.clear().catch(() => {});
    // If the previous session wrote anything to OPFS, drop the whole
    // session directory so the parent doesn't accumulate empty subdirs.
    const prevUsedOpfs = Object.values(prevBackends).some((b) => b === "opfs");
    if (prevUsedOpfs && prevOpfsSessionId) { /* remove session dir */ }
  }
}, []);
```

**Flow:** once per mount → read persisted session → reopen each track's store against the backend the PREVIOUS session actually used (missing field ⇒ pre-OPFS-migration ⇒ IDB everywhere) → gate on recoverable status ∧ ≥1 durable chunk → emit recovery-available telemetry → per track: iterate chunks, sort by index, rebuild webm blob, hand to `chrome.downloads.download` → revoke objectURL on a delayed 2000ms timer → only then clear all three stores → drop the whole OPFS session directory if any track used OPFS → toast the user.
**Invariant:** (1) download strictly before clear — the downloaded file is the user's only copy of a session that will never upload; clearing first destroys it; (2) `URL.revokeObjectURL` must be delayed because `chrome.downloads.download` resolves BEFORE Chrome fetches the blob — revoking immediately yields a zero-byte/failed download; (3) store reopen must honor the previous session's backend choice or recovery reads an empty store and silently skips rescue; (4) the once-guard prevents re-entry loops from React re-mounts double-downloading.
**Probe:** no upstream tests exist at pin. Deterministic anchors: grep CloudRecorder.jsx for `download() resolves before the blob fetch; delay revoke` (:3224), `matching pre-migration behaviour` (:3156), `recoveryAttempted.current = true` (:3148). Byte-exact at HEAD.

## Get live surrounding code
**Retrieve:**
```
trace_path(project="screenity", function_name="clearStaleUploadJournals", direction="both")
→ observed: single CloudRecorder caller chain — recovery path invokes sweep + telemetry together
search_graph(project="screenity", name_pattern="RECOVERABLE_SESSION_STATUSES")
→ observed: lines 124-131, in=1 (the isRecoverable gate at :3186 is its only consumer)
```

## Verdict
Adopt the ordering contract verbatim: detect (backend-aware) → gate (status ∧ durable bytes) → forensics → export → delayed revoke → clear → directory GC. Adapt the export channel (`chrome.downloads`) and the 2000ms revoke delay to your host's save mechanism. Omit the OPFS directory GC if your host has no directory-per-session layout.
