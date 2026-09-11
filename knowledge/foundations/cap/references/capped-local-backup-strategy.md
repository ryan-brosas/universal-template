<!-- capsule-v2 -->
# capped-local-backup-strategy — What is the minimal state machine for keeping a local backup copy of a streamed recording when storage is capped?

**Source:** cap AGPL-3.0 `main@0ce9e67516b14449c4263c0b173c85c40f30421b`; Codebase Memory `ext-cap`. **Question:** How does the capped strategy behave at overflow, and why is dropping EVERYTHING (not truncating) the correct move?

## off | full | capped(maxBytes); first byte past cap clears ALL chunks and latches overflowed — never a partial tail
**Path/Symbol:** `packages/recorder-core/src/local-recording-backup.ts:1-66` (whole module); fallback promotion `recording-spool-fallback.ts:1-28` (`moveRecordingSpoolToInMemoryBackup`).
**Signature:** `appendLocalRecordingChunk(state: LocalRecordingState, chunk: Blob, strategy: LocalRecordingStrategy): LocalRecordingState` (pure); `finalizeLocalRecording(state, fallbackMimeType?): Blob | null`.
**Data Shape:** `{chunks: Blob[], retainedBytes: number, overflowed: boolean}`; mime of final blob = first chunk's type ?? fallback ?? `"video/webm;codecs=vp8,opus"`.

### Decisive source
```ts
if (state.overflowed) { return state; }                    // latch: stay empty
if (state.retainedBytes + chunk.size > strategy.maxBytes) {
    return { chunks: [], retainedBytes: 0, overflowed: true };  // drop everything
}
```

**Flow:** Pure reducer — callers own persistence. `full` retains unconditionally; `capped` retains until one incoming chunk would cross maxBytes, then resets to empty+latched. Overflowed state ignores all further chunks. Finalize returns null when overflowed or empty (no partial backup), else concatenates chunks with the negotiated type. The spool-fallback helper promotes an IndexedDB spool to in-memory `full` mode by PREPENDING the recovered blob ahead of already-retained chunks (order = stream order).
**Invariant:** All-or-nothing capping keeps the backup a PLAYABLE prefix-free whole — MediaRecorder chunks are only concat-playable from the stream head, so retaining a suffix tail would yield an unplayable fragment. The recovered blob must precede retained chunks in any merged array.
**Probe:** `packages/recorder-core/__tests__/local-recording-backup.test.ts` — `retains a full local copy when configured for capped streaming backup` (:12), `drops the backup copy after the capped limit is exceeded` (:35).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-cap", query: "LocalRecordingStrategy appendLocalRecordingChunk", limit: 10 });
```

## Verdict
Adopt the pure reducer and all-or-nothing overflow semantics; adapt thresholds and storage ownership.
