<!-- capsule-v2 -->
# Finalize consumer ladder — in what order must a live session be drained, exported, and collapsed before the UI is told it ended?

**Source:** OpenOats MIT `main@bc0ddb9d5d12`; Codebase Memory `openoats`. **Question:** A porter ending a long-running capture must flush several independent subsystems (scratchpad, engine, cleaner, pending JSONL writes, audio recorder) and then decide between export/retain/discard/collapse — what order keeps every artifact consistent, and how does an empty duplicate session get folded into the real one?

## Ordered drain-then-decide finalize with ghost collapse and typed recovery results
**Path/Symbol:** `OpenOats/Sources/OpenOats/App/LiveSessionController.swift:finalizeCurrentSession` (:742–1052).
**Signature:** `func finalizeCurrentSession(settings: AppSettings?) async`.
**Data Shape:** Takes optional settings (nil disables all settings-gated branches); mutates coordinator UI state at the END; returns Void. All repository mutations happen through `coordinator.sessionRepository`; audio decisions come from the pure `audioRetentionPlan` (see sibling capsule).

### Decisive source
```swift
// 0. Flush scratchpad
scratchpadSaveTask?.cancel()
if let sessionID = _currentSessionID, !state.scratchpadText.isEmpty {
    await coordinator.sessionRepository.saveScratchpad(sessionID: sessionID, text: state.scratchpadText)
}
let captureHealthAtStop = coordinator.transcriptionEngine?.captureHealthSnapshot   // snapshot BEFORE finalize
...
// 1. Drain audio buffers
await coordinator.transcriptionEngine?.finalize()
// 1b. Drain pending cleanups
if let settings, settings.enableLiveTranscriptCleanup {
    await coordinator.liveTranscriptCleaner?.drain(timeout: .seconds(5))
}
// 2. Drain delayed JSONL writes
await coordinator.sessionRepository.awaitPendingWrites()
```
Ghost collapse (:936–948):
```swift
if utteranceCount == 0,
   let merged = await coordinator.sessionRepository.reconcileGhostSession(sessionID: sessionID) {
    mergedSessionID = merged
    effectiveIndex = await coordinator.sessionRepository.loadSession(id: merged).index   // RELOAD from target
    shouldRunBatchRetranscription = false                                                // suppress batch on merged row
    ...
}
```
Typed recovery result (:950–960):
```swift
if mergedSessionID != nil {
    recoveryResult = "collapsed_into_existing_session"
} else if queuedRecoveryBatch {
    recoveryResult = "queued"
} else if forcedRecoveryBatch && !retainedBatchAudio {
    recoveryResult = "unavailable_no_retained_audio"
} else {
    recoveryResult = "not_attempted"
}
```

**Flow:** (0) cancel scratchpad save task, flush non-empty scratchpad; snapshot capture-health/mute/peak BEFORE engine finalize → (1) engine.finalize drains audio buffers → (1b) cleaner.drain(5s) only if cleanup enabled → (2) `awaitPendingWrites()` so delayed enriched JSONL records land → (3) resolve sessionID (current ?? repo.getCurrentSessionID() ?? "unknown"), snapshot utterances, build title (currentTopic wins over metadata/calendar title) + RecordingHealthInput + transcriptIssue/classification → (4) `repository.finalizeSession` (closes handle, backfills cleaned text, writes session.json) → meeting-family folder preference update → (5) build SessionIndex → (5b/5c) webhook + Apple Notes fire-and-forget exports → (6) retention-plan branch: batch∧export ⇒ copy temp stems to NSTemporaryDirectory then stash + finalizeRecording; batch only ⇒ sealForBatch + stash; export only ⇒ finalizeRecording; neither ⇒ discardRecording → (7) if utteranceCount==0: reconcileGhostSession ⇒ effectiveIndex reloaded from merged target AND batch suppressed; record EmptySessionDiagnosticsEvent with recoveryResult ∈ {collapsed_into_existing_session, queued, unavailable_no_retained_audio, not_attempted}; set/clear pendingRecoveryDiagnostics → (8) reset UI state (`_currentSessionID = nil`, template snapshot cleared), `loadHistory()`, scheduleAutoNotesIfNeeded(waitForBatch:) → (9) detached batch-transcription Task only when enabled AND transcriber present.
**Invariant:** Every drain completes BEFORE any finalization write (scratchpad → engine → cleaner → pending JSONL writes), so the finalized transcript contains all enriched records; health snapshots are taken before the engine is torn down; a collapsed ghost never triggers a recovery batch and the UI's lastEndedSession points at the MERGED row, not the deleted ghost; the four-way recoveryResult vocabulary is exhaustive over (merged, queued, forced-without-audio, nothing).
**Probe:** `OpenOats/Tests/OpenOatsTests/LiveSessionControllerTests.swift:testFinalizeCurrentSessionCollapsesEmptyGhostSessionIntoRecentRealSession` (:645–698, seeds a real session 180s earlier with the same calendar event, starts+stops an empty ghost, asserts the ghost id is gone from listSessions, `lastEndedSession?.id == "session_real"`, and the merged detail carries the ghost's calendarEvent id).

## Get live surrounding code
**Retrieve:** (executed live at pin; Codebase Memory MCP not connected this session — direct source+test read fallback)
```bash
sed -n '742,1052p' OpenOats/Sources/OpenOats/App/LiveSessionController.swift  # whole ladder
sed -n '645,698p' OpenOats/Tests/OpenOatsTests/LiveSessionControllerTests.swift
```

## Verdict
Adopt the numbered drain-before-mutate ordering and the "reload the effective index from the merge target" step — both are what make collapse invisible to the UI. Adopt the closed-string recoveryResult vocabulary for empty-session telemetry. Adapt the export side effects (webhook/Apple Notes) to your host's integrations; omit the NSTemporaryDirectory copy hop if your recorder can hand off temp files directly. Coverage caveat: MCP graph not connected this pass; ranges read directly at pin bc0ddb9d.
