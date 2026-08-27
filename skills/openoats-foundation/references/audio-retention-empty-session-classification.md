<!-- capsule-v2 -->
# Audio retention plan + empty-session classification — how do you decide, from pure inputs, whether a session keeps its audio and what went wrong when it ended with zero text?

**Source:** OpenOats MIT `main@bc0ddb9d5d12`; Codebase Memory `openoats`. **Question:** A porter needs (a) a startup/finalize decision of start-recorder / retain-batch-audio / export / run-recovery-batch that works even when the user toggles are off, and (b) a diagnosis of an empty session that distinguishes "no audio at all" from "audio but no text" from "intentionally short" — how does OpenOats keep these decisions pure and testable?

## Pure retention plan where cloud-empty forces recovery; twin two-arm health ladders with different fall-throughs
**Path/Symbol:** `OpenOats/Sources/OpenOats/App/LiveSessionController.swift:audioRetentionPlan` (:1178–1188), `transcriptIssue(for:)` (:1195–1214), `recordingHealthNotice(for:)` (:1216–1259), `emptySessionDiagnosticClassification(for:)` (:1261–1281); input shape `RecordingHealthInput` (:105–116), `AudioRetentionPlan` (:98–103), classification enum (:67–71), issue enum `Models.swift:SessionTranscriptIssue` (:429).
**Signature:** `static func audioRetentionPlan(settings: AppSettings, utteranceCount: Int?) -> AudioRetentionPlan`; `static func transcriptIssue(for input: RecordingHealthInput) -> SessionTranscriptIssue?`; `static func emptySessionDiagnosticClassification(for input: RecordingHealthInput) -> EmptySessionDiagnosticClassification?`.
**Data Shape:** All four are pure static functions over value types (Equatable) — no actor, no I/O. `utteranceCount` is Optional in the plan (nil = startup, before any utterance exists).

### Decisive source
```swift
static func audioRetentionPlan(settings: AppSettings, utteranceCount: Int?) -> AudioRetentionPlan {
    let shouldRunRecoveryBatch = settings.transcriptionModel.isCloud && utteranceCount == 0
    let shouldRetainBatchAudio = settings.enableBatchRetranscription || shouldRunRecoveryBatch
    let shouldExportRecording = settings.saveAudioRecording
    let shouldStartRecorder = shouldExportRecording || shouldRetainBatchAudio || settings.transcriptionModel.isCloud
    return AudioRetentionPlan(...)
}
```
Shared ladder (identical in transcriptIssue and classification):
```swift
guard input.utteranceCount == 0 else { return nil }          // non-empty sessions never diagnosed
if let micCaptureError = input.micCaptureError, !micCaptureError.isEmpty {
    return .noAudioDetected
}
if input.elapsed >= 5,
   !input.systemHasCapturedFrames,
   (!input.isMicMuted && !input.micHasCapturedFrames) {
    return .noAudioDetected
}
if input.peakAudioLevel >= 0.04,
   input.micHasCapturedFrames || input.systemHasCapturedFrames {
    return .transcriptionProducedNoText
}
return nil                                                   // transcriptIssue fall-through
// vs `return .unclassified` in emptySessionDiagnosticClassification
```

**Flow:** plan: cloud model ∧ zero utterances ⇒ recovery batch, which transitively forces retain-batch-audio even with both user toggles off; any cloud model starts the recorder from t=0 so recovery audio exists; local models with options off do nothing. Diagnosis: only zero-utterance sessions enter; explicit capture error wins; ≥5s elapsed with no system frames and an unmuted mic that captured nothing ⇒ noAudioDetected; audible peak (≥0.04) with frames on either channel ⇒ transcriptionProducedNoText; otherwise the ISSUE returns nil (intentionally-short sessions stay unmarked) while the CLASSIFICATION returns .unclassified (telemetry must still record something). The live UI arm (`recordingHealthNotice`) is suppressed by blocking errors/pause, splits the 5s no-audio case into three device-specific warning messages, and adds a 20s stalled-transcription warning whose text gains a "recovery batch will run" suffix only for cloud models.
**Invariant:** The plan is a function of (model class, toggles, utterance count) alone — finalize re-evaluates it with the final count, so a cloud session that ends empty always has retained audio unless the recorder itself failed; the two ladders share their arms verbatim and differ ONLY in the fall-through (nil vs .unclassified), so a session can be unmarked in the UI yet still classified in telemetry.
**Probe:** `OpenOats/Tests/OpenOatsTests/LiveSessionControllerTests.swift:testAudioRetentionPlanKeepsRecoveryAudioForCloudLiveTranscription` (:936–955, cloud model with BOTH toggles off: startup plan retains nothing, zero-utterance plan retains batch audio AND runs recovery); `testAudioRetentionPlanDoesNotForceRecoveryForCloudSessionWithUtterances` (:957–969); `testAudioRetentionPlanLeavesLocalModelsUntouchedWhenRecordingOptionsAreOff` (:971–982); `testTranscriptIssueMarksMissingAudioForExtendedEmptySession` (:1240–1256), `testTranscriptIssueMarksStalledTranscriptionWhenAudioWasCaptured` (:1258–1275), `testTranscriptIssueLeavesIntentionallyEmptySessionUnmarked` (:1277–1292, 3s elapsed ⇒ nil); `testEmptySessionDiagnosticClassificationMarksMissingAudio` (:1404–1420); `testEmptySessionDiagnosticsMessageIsStructuredJSON` (:1422–1449, event round-trips through sortedKeys JSON).

## Get live surrounding code
**Retrieve:** (executed live at pin; Codebase Memory MCP not connected this session — direct source+test read fallback)
```bash
sed -n '1178,1290p' OpenOats/Sources/OpenOats/App/LiveSessionController.swift
sed -n '67,124p' OpenOats/Sources/OpenOats/App/LiveSessionController.swift   # enums/structs
sed -n '936,982p;1240,1292p;1404,1449p' OpenOats/Tests/OpenOatsTests/LiveSessionControllerTests.swift
```

## Verdict
Adopt the pure-plan pattern (value-in/value-out, re-evaluated at finalize with the final utterance count) and the "recovery forces retention" transitive rule — that is what makes silent-failure recovery possible without user opt-in. Adopt the shared-ladder/different-fall-through split between user-visible issue and telemetry classification. Adapt the thresholds (5s/20s/0.04 peak) to your capture stack; omit the Apple-specific device messages. Coverage caveat: MCP graph not connected this pass; ranges read directly at pin bc0ddb9d.
