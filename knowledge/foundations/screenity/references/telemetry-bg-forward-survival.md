<!-- capsule-v2 -->
# Telemetry BG-forward survival — how does an upload-telemetry event outlive the tab that emitted it?

**Source:** screenity GPL-3.0 `master@e10e375fafa1680de99ca6db36536dd4a1f4f7d4`; Codebase Memory `screenity`. **Question:** When a recorder tab can close at any moment (user click, pagehide), where must telemetry writes be routed so the last events are not dropped by a storage IPC race?

## Tab → service-worker telemetry relay with refcounted flush
**Path/Symbol:** `src/pages/CloudRecorder/CloudRecorder.jsx:appendUploadTelemetryEvent` (:650-664) + `flushInflightTelemetry` (:668-678); BG receiver `src/pages/Background/messaging/handlers.js` `registerMessage("cloud-telemetry-event", ...)` (:3062-3067).
**Signature:** `appendUploadTelemetryEvent(eventPayload) => Promise<void>`; `flushInflightTelemetry() => Promise<void>`.
**Data Shape:** `inflightTelemetryWritesRef` = `useRef(new Set())` of in-flight forward promises; each message is `{type: "cloud-telemetry-event", event}`; BG handler validates `event` is an object and returns `{ok}` from the serialized store append.

### Decisive source
```js
// Route telemetry writes through BG. window.close() races the
// storage IPC when written from this tab and the event drops; BG
// outlives the tab. Counter so the pre-close flush can await sends.
const inflightTelemetryWritesRef = useRef(new Set());
const appendUploadTelemetryEvent = async (eventPayload) => {
  const p = (async () => {
    try {
      await chrome.runtime.sendMessage({ type: "cloud-telemetry-event", event: eventPayload });
    } catch (err) { console.warn("Failed to forward upload telemetry event:", err); }
  })();
  inflightTelemetryWritesRef.current.add(p);
  p.finally(() => inflightTelemetryWritesRef.current.delete(p));
  return p;
};
const flushInflightTelemetry = async () => {
  const writes = Array.from(inflightTelemetryWritesRef.current);
  if (writes.length === 0) return;
  try {
    await Promise.race([
      Promise.allSettled(writes),
      // Hard cap so a wedged BG SW can't block tab close forever.
      new Promise((r) => setTimeout(r, 1500)),
    ]);
  } catch {}
};
```

**Flow:** emit → forward via runtime message (promise registered in the Set before any await) → BG receiver appends through the serialized store → close paths (`:3823`, `:6770`, `:6831`) `await flushInflightTelemetry()` immediately before `window.close()`/reload.
**Invariant:** the tab must never write telemetry storage directly on a path that can close, and the flush must be bounded — an unbounded await on BG turns a dead service worker into a tab that never closes. The Set self-cleans via `finally`, so flush sees only genuinely pending writes. The BG-side comment states the identical race rationale for perf marks: "a dying page racing storage.set drops the last few marks".
**Probe:** no upstream tests exist at pin (`tests/` untracked — dangling runner). Deterministic anchors: grep CloudRecorder.jsx for `window.close() races the` (:646) and `wedged BG SW can't block tab close forever` (:674); grep handlers.js for `Cloud upload telemetry routes here too` (:3061). Byte-exact at HEAD.

## Get live surrounding code
**Retrieve:**
```
search_graph(project="screenity", name_pattern="flushInflightTelemetry")
→ observed: 1 row, screenity.src.pages.CloudRecorder.CloudRecorder, lines 668-678, in=2 (exact match at pin)
trace_path(project="screenity", function_name="emitUploadTelemetry", direction="both")
→ observed: callers_total=26 (every lifecycle hook funnels here), callees_total=4 incl. appendUploadTelemetryEvent
```

## Verdict
Adopt the relay topology (tab emits → SW persists) and the refcounted allSettled-with-cap flush verbatim — it generalizes to any "log before unload" problem in MV3. Adapt the transport (`chrome.runtime.sendMessage`) and the 1500ms cap to your host's liveness budget. Omit Screenity's specific endpoint/key names.
