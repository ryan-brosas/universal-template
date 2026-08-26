<!-- capsule-v2 -->
# Offline recording buffer round-trip — how do you record with no network, persist to localStorage, and upload later with an honest time origin?

**Source:** OpenReplay AGPL-3.0 `main@99eb60032f70906f6887195c400f173c00a08522`; Codebase Memory `openreplay`. **Question:** What is the save→restore→upload protocol for offline sessions, and how do both sides agree on when the session actually started?

## App.offlineRecording / saveBuffer / uploadOfflineRecording / flushBuffer
**Path/Symbol:** `tracker/tracker/src/main/app/index.ts:offlineRecording` (:1340-1379), `saveBuffer` (:1388-1390), `uploadOfflineRecording` (:1413-1476), `flushBuffer` (:1761-1786), `bufferStorageKey = 'or_buffer_1'` (:75).
**Signature:** `public offlineRecording(startOpts = {}, onSessionSent: () => void)`; `public async uploadOfflineRecording()`; `private flushBuffer = async (buffer: Message[]) => Promise`.
**Data Shape:** localStorage key `or_buffer_1` holds JSON-serialized Message tuples; request fields `doNotRecord: boolean`, `bufferDiff: ms`, `isOffline: bool`; offline-end sentinel message `[[-1]]`.

### Decisive source
```ts
const saverBuffer = this.localStorage.getItem(bufferStorageKey)
if (saverBuffer) {
  const data = JSON.parse(saverBuffer)
  this.bufferedMessages1 = Array.isArray(data) ? data : this.bufferedMessages1
  this.localStorage.removeItem(bufferStorageKey)      // restore-once semantics
}
...
// upload side:
while (this.bufferedMessages1.length > 0) {
  await this.flushBuffer(this.bufferedMessages1)       // splice per Timestamp boundary
}
this.postToWorker([[-1]] as unknown as Message[])        // offline-end sentinel → finaliseBatch + onOfflineEnd
```
Server twin (`backend/pkg/sessions/api/web/handlers.go:getSessionTimestamp` :74-83):
```go
if req.IsOffline { return uint64(req.Timestamp) }         // device clock wins for offline
ts := uint64(startTimeMili)
if req.BufferDiff > 0 && req.BufferDiff < 5*60*1000 { ts -= req.BufferDiff } // cold-start credit ≤5min
```

**Flow:** offlineRecording → preload+clear any saved buffer → ColdStart state captures into bufferedMessages1 → app calls saveBuffer() at its own discretion (size discipline is the embedder's job) → later, uploadOfflineRecording stops capture, starts a REAL worker session (`doNotRecord:false`, `bufferDiff: timestamp - coldStartTs`), awaits /v1/web/start, then drains the buffer through flushBuffer which SPLICES at Timestamp boundaries (first element always a Timestamp; batch ends before the next one) and posts to the worker → `[[-1]]` sentinel makes BatchWriter finalise and fire onSessionSent.
**Invariant:** Offline sessions trust DEVICE time exclusively (`IsOffline → req.Timestamp`) because server-relative delay correction is meaningless across a gap — documented in the singleton docstring. The 5-minute BufferDiff ceiling prevents a stale cold-start timestamp from rewriting a live session's start time. Proxy-object hazard is handled explicitly: messages pass through `.map((x) => [...x])` because reactive frameworks (vue) hand proxies that structured-clone badly.
**Probe:** `grep -n 'BufferDiff > 0 && req.BufferDiff < 5\*60\*1000' backend/pkg/sessions/api/web/handlers.go` from repo root → line 79; `grep -n "splice(0, endIndex)" tracker/tracker/src/main/app/index.ts` → line 1775 (both verified live). Coverage caveat: Go handler has no direct test in-repo; pinned by source anchor only.
**Retrieve:** search_graph project openreplay query "uploadOfflineRecording saveBuffer bufferStorageKey" → rank-1 `App.saveBuffer :1388-1390` line-exact at pin.

## Verdict
Adopt restore-once storage round-trip, Timestamp-boundary splicing, sentinel-driven finalisation, and IsOffline/BufferDiff start-time algebra as pure behavior; adapt localStorage to your persistence layer; omit the localDebug onLocalSave artifact dump if you don't need wire debugging.
