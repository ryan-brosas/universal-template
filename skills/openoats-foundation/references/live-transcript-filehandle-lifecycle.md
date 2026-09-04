<!-- capsule-v2 -->
# Live transcript file-handle lifecycle — when is the live JSONL handle opened, kept open, and closed?

**Source:** OpenOats MIT `main@bc0ddb9d5d12`; Codebase Memory `openoats`. **Question:** During live recording, does every appended utterance pay an open/append/close cycle, or is the handle held — and where exactly is it released?

## Held-open append handle
**Path/Symbol:** `OpenOats/Sources/OpenOats/Storage/SessionRepository.swift:openLiveTranscriptFileHandle` (:1823–1844); open sites: `startSession` :271, `resumeAbandonedSession` :299; close sites: `finalizeSession` :431–432 (`try? liveFileHandle?.close(); liveFileHandle = nil`).
**Signature:** `private func openLiveTranscriptFileHandle(sessionID: String)`; state `private var liveFileHandle: FileHandle?` (:189).
**Data Shape:** Creates `transcript.live.jsonl` via `FileManager.createFile(contents: nil, attributes: [.posixPermissions: 0o600])` only if absent, then opens for writing and seeks to end (append-safe on resume).

### Decisive source
```swift
if !fm.fileExists(atPath: liveFile.path) {
    fm.createFile(atPath: liveFile.path, contents: nil,
                  attributes: [.posixPermissions: 0o600])
}
do {
    let handle = try FileHandle(forWritingTo: liveFile)
    handle.seekToEndOfFile()
    liveFileHandle = handle
} catch {
    reportWriteError("Failed to open live transcript file: \(error.localizedDescription)")
}
```

**Flow:** start/resume session → close stale handle → create-if-missing with 0600 → open write handle → seekToEndOfFile → every `appendRecord` writes through the held handle → `finalizeSession` closes it and clears `currentSessionID`.
**Invariant:** The handle spans the whole recording session (10 appends in the direct test all land without reopen); permissions are set at creation time, not per-append; a failed open surfaces once through `reportWriteError` instead of throwing.

**Probe:** `OpenOats/Tests/OpenOatsTests/SessionRepositoryTests.swift:testFileHandleStaysOpenDuringRecording` (:749–765) — 10 sequential `appendLiveUtterance` calls then `endSession`; asserts all 10 records load back from the transcript.

## Get live surrounding code
**Retrieve:** (executed live at pin; top hit = target test, rank 2 = source)
```ts
await mcp.codebase_memory.search_graph({ project: "openoats", query: "openLiveTranscriptFileHandle keeps FileHandle open during recording", limit: 10, fields: ["signature", "file"] });
// → rank 1: SessionRepositoryTests.testFileHandleStaysOpenDuringRecording :749-765;
//   rank 2: …SessionRepository.openLiveTranscriptFileHandle :1823-1844
```

## Verdict
Adopt hold-open-for-session append semantics with create-time permission stamping and seek-to-end resume. Adapt to your runtime's equivalent of FileHandle (e.g. O_APPEND fd). Omit the silent `try?` teardown on close if your host can log it. Coverage caveat: both cited paths are no_recorded_issue + metadata_match at gen 2026-08-25T19:59:34Z.
