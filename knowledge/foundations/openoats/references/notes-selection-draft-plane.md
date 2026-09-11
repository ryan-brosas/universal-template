<!-- capsule-v2 -->
# Notes selection + unsaved-draft plane — how do you switch between sessions without losing an unsaved draft or leaking the previous session's state?

**Source:** OpenOats MIT `main@bc0ddb9d5d12`; Codebase Memory `openoats`. **Question:** A porter building a session-detail view must reset a large UI state on every selection and load several independent artifacts — how does OpenOats guarantee (a) no field from the previous session survives, (b) an unsaved manual-notes draft follows its session across switches, and (c) loads don't race each other?

## Reset-then-load selection with a per-session in-memory draft map
**Path/Symbol:** `OpenOats/Sources/OpenOats/App/NotesController.swift:selectSession` (:290–391), `persistCurrentManualNotesDraftIfNeeded` (:1250–1258), `updateManualNotesDraft` (:758–769), `saveManualNotes` (:781–808), `loadHistory` (:1312–1317) + `startMeetingHistoryPreviewHydration` (:1351–1383); draft map `unsavedManualNotesDraftsBySessionID` (:179, `@ObservationIgnored`).
**Signature:** `func selectSession(_ sessionID: String?)`; `private func persistCurrentManualNotesDraftIfNeeded()`; `func updateManualNotesDraft(_ markdown: String)`; `func loadHistory() async`.
**Data Shape:** selectSession is synchronous for the reset and spawns ONE Task for all loading; nil selection clears every loaded field and returns. The draft map is deliberately outside observation (not UI state) so keystrokes don't trigger view invalidation storms.

### Decisive source
```swift
func selectSession(_ sessionID: String?) {
    persistCurrentManualNotesDraftIfNeeded()      // park outgoing session's draft FIRST
    cancelMeetingHistoryPreviewHydration()
    cancelMeetingFamilyKnowledgeBaseLoad()
    ...
    stopAudio()
    guard let sessionID else { /* clear ~18 fields */ return }
    state.loadedNotes = nil
    state.manualNotesDraft = ""
    ...                                            // EVERY loaded field reset to default BEFORE loading
    Task {
        async let sessionData = coordinator.sessionRepository.loadSessionData(sessionID: sessionID)
        async let canRetranscribe = coordinator.sessionRepository.hasRetainedBatchAudio(sessionID: sessionID)
        async let hasBackup = coordinator.sessionRepository.hasPreBatchTranscriptBackup(sessionID: sessionID)
        async let customGuidance = coordinator.sessionRepository.loadCustomNotesGuidance(sessionID: sessionID)
        async let scratchpad = coordinator.sessionRepository.loadScratchpad(sessionID: sessionID)
        ...
        let unsavedDraft = unsavedManualNotesDraftsBySessionID[sessionID]
        state.manualNotesDraft = unsavedDraft ?? data.notes?.markdown ?? ""
        state.isEditingManualNotes = unsavedDraft != nil
```
Draft parking (:1250–1258):
```swift
private func persistCurrentManualNotesDraftIfNeeded() {
    guard let sessionID = state.selectedSessionID, state.loadedTranscript.isEmpty else { return }
    if state.manualNotesDraft.isEmpty || state.manualNotesDraft == state.savedManualNotesMarkdown {
        unsavedManualNotesDraftsBySessionID.removeValue(forKey: sessionID)
    } else {
        unsavedManualNotesDraftsBySessionID[sessionID] = state.manualNotesDraft
    }
}
```

**Flow:** switch ⇒ park outgoing draft (only transcript-less sessions keep drafts; draft equal to saved markdown or empty ⇒ drop the entry) → cancel preview hydration + KB load + audio → reset ALL loaded fields to defaults (nil-selection path returns here) → one Task fans out with `async let` over loadSessionData / hasRetainedBatchAudio / hasPreBatchTranscriptBackup / guidance / scratchpad → incoming draft lookup wins over saved markdown and sets isEditingManualNotes → template + meeting-family presentation → cleanup status derived from whether any record has cleanedText → pending auto-notes fire only if still selected AND transcript non-empty. Keystrokes (`updateManualNotesDraft`) keep the map live; `saveManualNotes` persists then removes the entry, guarding against the selection having changed mid-save. History previews hydrate lazily in a cancellable Task that re-checks the family key per item and skips writes when values are unchanged.
**Invariant:** No field from the previous session can survive a switch because every loaded field is reset to its default BEFORE any async load resolves; a draft belongs to exactly one session id and is dropped when it stops differing from the saved markdown; concurrent loads are grouped in one Task so a fast double-switch cancels via the per-field re-checks rather than interleaving two half-loaded states.
**Probe:** `OpenOats/Tests/OpenOatsTests/NotesControllerTests.swift:testSelectSessionLoadsTranscriptAndNotes` (:126–141, selectedSessionID set, 3 transcript records loaded, loadedNotes nil before generation); `testUnsavedManualNotesDraftSurvivesSessionSwitch` (:586–606, edit draft on "manual", switch to "other" and back, draft text intact, isEditingManualNotes true, loadedNotes still nil).

## Get live surrounding code
**Retrieve:** (executed live at pin; Codebase Memory MCP not connected this session — direct source+test read fallback)
```bash
sed -n '290,391p' OpenOats/Sources/OpenOats/App/NotesController.swift     # selectSession
sed -n '1250,1258p;758,808p' OpenOats/Sources/OpenOats/App/NotesController.swift
sed -n '126,141p;586,606p' OpenOats/Tests/OpenOatsTests/NotesControllerTests.swift
```

## Verdict
Adopt reset-before-load (defaults first, async fill second) as the anti-leak rule for any large detail state, and the "draft parked only while it differs from saved" lifecycle for unsaved edits. Adapt the @ObservationIgnored detail to your observation framework (keep the draft map out of reactive state). Omit the meeting-family presentation branches if you have no recurring-meeting concept. Coverage caveat: MCP graph not connected this pass; ranges read directly at pin bc0ddb9d.
