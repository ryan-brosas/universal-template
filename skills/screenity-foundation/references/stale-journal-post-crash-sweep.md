<!-- capsule-v2 -->
# Stale journal post-crash sweep — what must be deleted after a crash so the next session cannot append to a dead upload?

**Source:** screenity GPL-3.0 `master@e10e375fafa1680de99ca6db36536dd4a1f4f7d4`; Codebase Memory `screenity`. **Question:** Which persisted keys survive a recorder-tab crash, and why does leaving even one of them produce a corrupted video?

## Journal + lookup + video-map + sceneId key sweep with pre-removal telemetry
**Path/Symbol:** `src/pages/CloudRecorder/CloudRecorder.jsx:clearStaleUploadJournals` (:3067-3144); single caller = session recovery path (trace: callers_total=1).
**Signature:** `clearStaleUploadJournals(storedSession) => Promise<void>`.
**Data Shape:** input = persisted `recorderSession` with `tracks: {screen|camera|audio: {uploader: {journalKey, journalLookupKey, projectId, sceneId, type/trackType, ...}}}`; key families removed: per-track `journalKey`/`journalLookupKey`, composite `` `bunnyVideoMap-${pid}-${sid || "none"}-${t || "none"}` ``, and global `sceneId`/`sceneIdStatus`.

### Decisive source
```js
// Removes stale TUS journals, lookup keys, and Bunny video-map entries that
// survive a process crash. Without this, the next session can resume the old
// partial Bunny upload and append fresh chunks, producing a garbled video.
// Also resets sceneId so the next session gets a fresh scene.
const clearStaleUploadJournals = async (storedSession) => {
  const keysToRemove = [];
  const tracks = storedSession?.tracks || {};
  for (const trackData of Object.values(tracks)) {
    const upl = trackData?.uploader;
    if (!upl) continue;
    if (upl.journalKey) keysToRemove.push(upl.journalKey);
    if (upl.journalLookupKey) keysToRemove.push(upl.journalLookupKey);
    const pid = upl.projectId || storedSession?.projectId || null;
    // ...
    if (pid && t) keysToRemove.push(`bunnyVideoMap-${pid}-${sid || "none"}-${t || "none"}`);
  }
  // Reset sceneId so getOrCreateSceneId doesn't reuse a scene tied to cleared journals.
  keysToRemove.push("sceneId", "sceneIdStatus");
  const uniqKeys = [...new Set(keysToRemove)];
  void emitUploadTelemetry("upload_recovery_journals_cleared", { reason: "post-crash-recovery",
    clearedKeyCount: uniqKeys.length, /* per-track journal offsets/status for forensics */ });
  if (!uniqKeys.length) return;
  try { await chrome.storage.local.remove(uniqKeys); }
  catch (err) { console.warn("[CloudRecorder] clearStaleUploadJournals: failed to remove keys", /*...*/); }
};
```

**Flow:** collect per-track journal keys → derive composite video-map keys from projectId/sceneId/trackType (with `"none"` placeholders so a missing sceneId still yields the right key shape) → always add sceneId reset keys → dedupe → emit forensic telemetry BEFORE deleting (fire-and-forget, carries old offsets/status/mediaIds that will be gone afterward) → remove in one batch; removal failure only warns.
**Invariant:** (1) every key family must go — resuming the OLD partial upload while appending FRESH chunks is the exact garbled-video failure this sweep exists to prevent; (2) the sceneId reset is part of the same atomic sweep because `getOrCreateSceneId` would otherwise reattach the new session to a scene whose journals were just destroyed; (3) telemetry must fire before removal since it documents state being destroyed; (4) a failed removal degrades to a warning, never blocks recovery.
**Probe:** no upstream tests exist at pin. Deterministic anchors: grep CloudRecorder.jsx for `producing a garbled video` (:3069) and `bunnyVideoMap-` (:3087). Byte-exact at HEAD.

## Get live surrounding code
**Retrieve:**
```
search_graph(project="screenity", name_pattern="clearStaleUploadJournals")
→ observed: 1 row, lines 3071-3144, in=1 out=7 (exact match at pin)
trace_path(project="screenity", function_name="clearStaleUploadJournals")
→ observed: callers_total=1 (CloudRecorder), callees_total=5 incl. emitUploadTelemetry — the sweep funnels into the same telemetry trio
```

## Verdict
Adopt the "destroy resume identity before starting fresh" contract: journals + lookup keys + server-side video map + scene identity in one sweep, with pre-destruction forensics. Adapt key naming/composite-key shapes to your uploader's persistence. Omit the Bunny video-map family if your host keeps no server-side offset map.
