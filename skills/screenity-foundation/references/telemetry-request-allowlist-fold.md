<!-- capsule-v2 -->
# Telemetry request allowlist + error fold — which fields reach the server, and which events survive before mediaId exists?

**Source:** screenity GPL-3.0 `master@e10e375fafa1680de99ca6db36536dd4a1f4f7d4`; Codebase Memory `screenity`. **Question:** How do you map a loose diagnostic payload onto a strict server schema without either dropping pre-mediaId diagnostics or risking the whole body on unknown keys?

## Typed allowlist with diagnostic-type gate and errMsg fold
**Path/Symbol:** `src/pages/CloudRecorder/CloudRecorder.jsx:toUploadTelemetryRequest` (:711-966).
**Signature:** `toUploadTelemetryRequest(eventPayload) => Promise<requestBody | null>` (null = event must not be sent).
**Data Shape:** output `{recordingId, recordingSessionId, projectId, sceneId, mediaId, bunnyVideoId, source: "extension", extVersion, env: {...}, event: {type, t, name?, tMs?, ...typed diag fields}}`; every optional field is typeof-gated to null; gate set: mediaId OR `event === "recording_outcome"` OR membership in `DIAG_EVENT_TYPES`.

### Decisive source
```js
const DIAG_EVENT_TYPES = new Set([
  "recording_heartbeat", "recording_stop_diag", "recording_failed_bundle",
  // Fires when a track dies during setup, exactly when its uploader has no
  // meta yet, so the guard below would drop it silently.
  "recording_track_setup_failed_after_live",
]);
if (!mediaId && eventPayload.event !== "recording_outcome" && !DIAG_EVENT_TYPES.has(eventPayload.event)) {
  return null;
}
// ...
// errMsg first: callers passing the server's own field name were
// silently nulled here for as long as the mapping has existed.
errMsg: eventPayload.errMsg || eventPayload.message || eventPayload.error || null,
```
and at the tail of the nested `event` object:
```js
// Diagnostic event fields. ... In `event`, not at the request root: nested objects here are a
// shape the server sanitizes, an unknown root key risks the body.
```

**Flow:** resolve mediaId from payload → screen-uploader meta → camera-uploader meta; if absent, admit only allowlisted diagnostic types and `recording_outcome` (server joins them by recordingSessionId) → project every field through a typed allowlist (number/boolean/string typeof checks, else null) → fold error text `errMsg || message || error`.
**Invariant:** (1) unknown root keys are dropped client-side — "an unknown root key risks the body" server-side, while nested objects sanitize cleanly, so all diagnostic payloads live in the nested `event` object; (2) diagnostics that fire *before* an uploader has meta need an explicit admission list or they vanish silently at exactly the most interesting moment (track death during setup); (3) the error-text fold must try the server's own field name first — callers using `message`/`error` were silently nulled for the mapping's entire lifetime; (4) module-global fallbacks (encoderKind, encoderStickyDisabled, recordingType, micActive…) let post-startup events carry context no caller threads explicitly.
**Probe:** no upstream tests exist at pin. Deterministic anchors: grep CloudRecorder.jsx for `would drop it silently` (:724), `silently nulled here for as long as the mapping has existed` (:862-863), `an unknown root key risks the body` (:946). Byte-exact at HEAD.

## Get live surrounding code
**Retrieve:**
```
search_graph(project="screenity", name_pattern="toUploadTelemetryRequest")
→ observed: 1 row, lines 711-966, in=1 out=14 (exact match at pin; single caller = sendUploadTelemetryNetwork)
```

## Verdict
Adopt the three contracts verbatim: admit-list-before-mediaId, nested-only diagnostics, server-field-name-first error fold. Adapt the concrete field names/types to your schema. Omit Screenity's bunnyVideoId/encoder-slot vocabulary unless you run the same dual-uploader cloud pipeline.
