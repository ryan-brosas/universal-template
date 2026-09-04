<!-- capsule-v2 -->
# Telemetry store write chain — how does the BG event log survive concurrent appends and its own failures?

**Source:** screenity GPL-3.0 `master@e10e375fafa1680de99ca6db36536dd4a1f4f7d4`; Codebase Memory `screenity`. **Question:** When many async producers append to one `chrome.storage.local` ring buffer, what serialization and failure contract prevents both lost-update clobbers and telemetry crashing recording?

## Promise-chained read-modify-write over a bounded ring
**Path/Symbol:** `src/pages/Background/utils/serializedTelemetryStore.js:appendUploadTelemetryEventSerialized` (:6-33, whole file is 33 lines).
**Signature:** `appendUploadTelemetryEventSerialized(event) => Promise<boolean>` (true = persisted, false = dropped-but-logged).
**Data Shape:** module state: `STORAGE_KEY = "cloudUploadTelemetryEvents"`, `MAX_EVENTS = 300`, `writeChain` initialized to `Promise.resolve()`. Storage layout: array under STORAGE_KEY plus a mirror scalar `lastUploadTelemetryEvent`.

### Decisive source
```js
let writeChain = Promise.resolve();
export const appendUploadTelemetryEventSerialized = async (event) => {
  if (!event || typeof event !== "object") return false;
  const job = writeChain.then(async () => {
    const existing = await chrome.storage.local.get([STORAGE_KEY]);
    const current = Array.isArray(existing?.[STORAGE_KEY]) ? existing[STORAGE_KEY] : [];
    const next = [...current, event].slice(-MAX_EVENTS);
    await chrome.storage.local.set({ [STORAGE_KEY]: next, lastUploadTelemetryEvent: event });
  });
  writeChain = job.catch(() => {});
  try { await job; return true; }
  catch (err) {
    // Don't throw (telemetry can't break recording), but log loudly: silent
    // event loss is the bug this serializer was added to fix.
    console.warn("[serializedTelemetryStore] write failed; event lost:", err?.message || err,
      { eventType: event?.event || event?.type || null });
    return false;
  }
};
```

**Flow:** validate shape → enqueue read-modify-write behind the previous job → cap array at last 300 → write array + mirror of the newest event → caller gets a boolean; the chain itself swallows errors so one failure never poisons later appends.
**Invariant:** (1) every read-modify-write must run inside the chain or two concurrent appends clobber each other's array snapshot; (2) the store must never throw into recording code paths — but a failure must be *loud*, because silent event loss is exactly the defect this serializer exists to fix; (3) the mirror key gives crash forensics the single newest event without reading the array.
**Probe:** no upstream tests exist at pin (`tests/` untracked). Deterministic anchors: grep serializedTelemetryStore.js for `silent` + `event loss is the bug this serializer was added to fix` (:25) and `.slice(-MAX_EVENTS)` (:13). Byte-exact at HEAD.

## Get live surrounding code
**Retrieve:**
```
get_code_snippet(project="screenity", qualified_name="screenity.src.pages.Background.utils.serializedTelemetryStore.appendUploadTelemetryEventSerialized")
→ observed: served source :6-33 byte-identical to checkout; callers=2 (BG message handler + BG recordingHelpers)
search_graph(project="screenity", name_pattern="appendUploadTelemetryEvent")
→ observed: 2 rows — BG appendUploadTelemetryEventSerialized :6-33 AND tab-side appendUploadTelemetryEvent :650-664 (same relay, different tiers)
```

## Verdict
Adopt the write-chain serialization, the never-throw/loud-warn split, and the newest-event mirror key as-is — they are host-agnostic. Adapt MAX_EVENTS and the storage backend to your host. Omit nothing else; the file has no product coupling.
