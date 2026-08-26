<!-- capsule-v2 -->
# recording-spool-liveness-contract — How do you back a browser recording in IndexedDB so crash recovery never deletes a LIVE session's backup?

**Source:** cap AGPL-3.0 `main@0ce9e67516b14449c4263c0b173c85c40f30421b`; Codebase Memory `ext-cap`. **Question:** What distinguishes a live spool from an orphaned one when chunk writes pause (paused MediaRecorder), and what are the queue/backpressure rules?

## updatedAt heartbeat (15s) + 3-minute idle window decide liveness; chunk writes alone are NOT a liveness signal
**Path/Symbol:** `packages/recorder-core/src/recording-spool.ts:41-51` (contract constants), `:211-401` (`RecordingSpool`), recovery sweeps `:406-486` (`recoverOrphanedRecordingSpools`, `recoverRecordingSpoolSession`).
**Signature:** `RECORDING_SPOOL_LIVE_MIN_IDLE_MS = 3 * 60 * 1000; RECORDING_SPOOL_HEARTBEAT_INTERVAL_MS = 15 * 1000`; `touch(): Promise<void>`; `appendChunk(chunk: Blob)`; static `create(options, backend?)`.
**Data Shape:** IDB `cap-recording-spool` v1: `sessions` store keyed `sessionId` (`{sessionId,mimeType,totalBytes,chunkCount,createdAt,updatedAt}`); `chunks` store keyPath `["sessionId","index"]` + non-unique index `by-session`. Default backlog cap 32 MiB pending.

### Decisive source
```ts
// Liveness contract between live recorders and recovery sweeps: a spool whose
// session was updated within this window must be treated as live and never
// offered as "recovered" (dismissing a recovered spool deletes the live
// session's crash backup out from under it). Chunk writes alone are not a
// reliable liveness signal — a paused MediaRecorder produces no chunks — so
// recorders also call RecordingSpool.touch() on the heartbeat interval below.
// The window is sized at 3x the worst-case heartbeat cadence: background tabs
// under Chrome's intensive timer throttling fire intervals as rarely as once
// per minute.
```

**Flow:** All writes funnel through one promise chain (`enqueue`) — strictly increasing chunk indexes even under overlapping appends. A write failure latches `writeError`: every later append rejects fast, but queued in-memory chunks stay recoverable (`recoverBlob` = persisted + pending). Backlog > 32 MiB raises `RecordingSpoolBackpressureError` immediately. `touch()` refreshes updatedAt WITHOUT a chunk on the same queue; touch failures are swallowed so they can't poison the queue. Recovery sweep skips sessions with `now − updatedAt < minIdleMs`, sorts newest-first, and NEVER deletes — dismissal is an explicit `deleteRecoveredRecordingSpool`.
**Invariant:** Dismissing a "recovered" recording must never destroy a live session's backup ⇒ idle-window skip is mandatory. Heartbeat window = 3× worst-case throttled interval. One write error poisons the session permanently (fail-fast over silent partial state).
**Probe:** `packages/recorder-core/__tests__/recording-spool.test.ts` — `skips recently updated spools so live cross-tab recordings are not offered as recovered` (:376), `touch refreshes updatedAt so paused recordings stay invisible to recovery sweeps` (:419), `keeps queued chunk indexes unique when appends overlap` (:161), `fails fast when the pending spool backlog grows beyond its limit` (:204).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-cap", query: "RecordingSpool recoverOrphanedRecordingSpools touch", limit: 10 });
```

## Verdict
Adopt the heartbeat+idle-window contract, single-writer queue with latch-on-error, and read-only recovery sweep. Adapt store layout to your storage layer.
