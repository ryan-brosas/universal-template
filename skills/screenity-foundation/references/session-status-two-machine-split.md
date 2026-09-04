<!-- capsule-v2 -->
# Session status two-machine split — which status set gates uploader resume, and which gates crash recovery?

**Source:** screenity GPL-3.0 `master@e10e375fafa1680de99ca6db36536dd4a1f4f7d4`; Codebase Memory `screenity`. **Question:** When a porter models "can I retry this upload?" vs "was this session interrupted?", why must those be two different state machines?

## Per-uploader RESUMABLE set vs per-session RECOVERABLE set
**Path/Symbol:** `src/pages/CloudRecorder/CloudRecorder.jsx` — `RESUMABLE_UPLOADER_STATUSES` (:86-91), `RECOVERABLE_SESSION_STATUSES` (:124-131); consumers: stall sweep :2823-2833, network-online handler :5763-5780, recovery gate :3186-3191.
**Signature:** `RESUMABLE_UPLOADER_STATUSES: Set<"uploading"|"paused"|"error"|"ready">`; `RECOVERABLE_SESSION_STATUSES: Set<"recording"|"hidden"|"unload"|"stopping"|"finalize-failed"|"upload-stalled">`.
**Data Shape:** uploader status lives on each track's uploader instance (`uploader.status`, plus `isPaused`, failure counters per track); session status lives on the persisted recorderSession object.

### Decisive source
```js
// Statuses a plain resume() recovers. Shared by the network-online handler and
// the per-track stall sweep.
const RESUMABLE_UPLOADER_STATUSES = new Set(["uploading", "paused", "error", "ready"]);
```
```js
const RECOVERABLE_SESSION_STATUSES = new Set([
  "recording", "hidden", "unload", "stopping", "finalize-failed", "upload-stalled",
]);
```
Stall-sweep consumer (one of two resume sites):
```js
// Same action the online handler takes. resume() restarts processQueue
// and, on a recoverable error, the heartbeat that HEAD-resyncs.
if (RESUMABLE_UPLOADER_STATUSES.has(uploader.status)) {
  try { uploader.resume(); } catch (err) { /* warn */ }
  // Without this the write path re-pauses on the next single failure,
  // and every later chunk is dropped at the isPaused check.
  const counter = uploaderFailureCounters[track];
  if (counter) counter.current = 0;
}
```
Recovery gate:
```js
const isRecoverable = RECOVERABLE_SESSION_STATUSES.has(storedSession?.status);
const hasDurableChunks = chunkCount > 0 || cameraChunkCount > 0 || audioChunkCount > 0;
if (storedSession && isRecoverable && hasDurableChunks) { /* recover */ }
```

**Flow:** runtime retry = uploader-level: both the `online` event and the 5s stall sweep call `resume()` only for the four resumable statuses, and reset that track's failure counter so a transient blip doesn't leave the write path latched paused → process restart = session-level: a NEW CloudRecorder mount reads the persisted session, requires BOTH a recoverable lifecycle status AND at least one durable chunk, then downloads-and-clears (see crash-recovery capsule).
**Invariant:** (1) the sets must not be merged or reused across tiers — "paused" is resumable in-process but meaningless as a crash-recovery signal, while "finalize-failed" triggers recovery but must never be fed to `resume()`; (2) resume without the counter reset re-pauses on the next single failure (every later chunk silently dropped at the isPaused check); (3) recovery additionally requires durable chunks so a session that died before writing anything doesn't trigger a bogus recovery download.
**Probe:** no upstream tests exist at pin. Deterministic anchors: grep CloudRecorder.jsx for `Statuses a plain resume() recovers` (:84-85 comment), `Without this the write path re-pauses` (:2829-2830), `RECOVERABLE_SESSION_STATUSES.has(` at :3186. Byte-exact at HEAD.

## Get live surrounding code
**Retrieve:**
```
search_graph(project="screenity", name_pattern="RESUMABLE_UPLOADER_STATUSES")
→ observed: 1 row, lines 86-91, in=2 (exact match at pin)
search_graph(project="screenity", name_pattern="RECOVERABLE_SESSION_STATUSES|SESSION_STATE_INDEX_KEY")
→ observed: 2 rows — RECOVERABLE_SESSION_STATUSES :124-131 (in=1), SESSION_STATE_INDEX_KEY :123 (in=2)
```

## Verdict
Adopt the tier split (uploader-status machine for runtime retries, session-status machine for post-crash decisions) and the resume+counter-reset pairing as one atomic move. Adapt status vocabularies to your uploader FSM. Omit nothing — the comment-documented coupling between sweep and online handler is the design.
