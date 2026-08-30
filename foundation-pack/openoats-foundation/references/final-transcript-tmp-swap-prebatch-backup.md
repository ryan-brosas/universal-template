<!-- capsule-v2 -->
# Final-transcript tmp-swap + pre-batch backup — how is a destructive final-transcript overwrite made recoverable?

**Source:** OpenOats MIT `main@bc0ddb9d5d12`; Codebase Memory `openoats`. **Question:** When a batch re-transcription replaces the final transcript wholesale, what must be backed up, in what order, and what metadata side-effects mark the recovery?

## Backup-then-atomic-swap overwrite ladder
**Path/Symbol:** `OpenOats/Sources/OpenOats/Storage/SessionRepository.swift:saveFinalTranscript` (:565–630) + `backupTranscriptForBatchOverwrite` (:651–675); restore path `restorePreBatchTranscript` (:1443–1451), `hasPreBatchTranscriptBackup` (:1433–1441).
**Signature:** `func saveFinalTranscript(sessionID: String, records: [SessionRecord], backupCurrentTranscript: Bool = false, markAsRecoveredIfIssuePresent: Bool = false)`
**Data Shape:** Files in `sessions/<id>/`: `transcript.final.jsonl` (target), `.tmp` staging twin, `transcript.pre-batch.jsonl` (backup). Metadata refresh derives `startedAt`/`endedAt` from the new records' first/last timestamps.

### Decisive source
```swift
if backupCurrentTranscript { backupTranscriptForBatchOverwrite(sessionID: sessionID) }
// ...
try payload.write(to: tempURL, options: .atomic)
if fm.fileExists(atPath: finalURL.path) { try fm.removeItem(at: finalURL) }
try fm.moveItem(at: tempURL, to: finalURL)
// backup source selection:
if fm.fileExists(finalURL), let data = try? Data(contentsOf: finalURL), !data.isEmpty { sourceURL = finalURL }
else if fm.fileExists(liveURL),  let data = try? Data(contentsOf: liveURL),  !data.isEmpty { sourceURL = liveURL }
else { return }   // nothing non-empty to back up → no backup file
```
and the metadata tail: `transcriptIssue: nil`, `transcriptRecovery = markAsRecoveredIfIssuePresent && meta.transcriptIssue != nil ? .recoveredAfterBatch : nil`.

**Flow:** (opt) back up non-empty final, else non-empty live, else skip → write full JSONL payload to `.tmp` atomically → remove existing final → moveItem tmp→final → reload metadata, clear transcriptIssue, optionally stamp `.recoveredAfterBatch`, re-derive startedAt/endedAt from records → scheduleMirror.
**Invariant:** The backup is taken BEFORE any destructive step; a backup is only created from non-empty content (an empty prior state needs no recovery); the final file is never observed half-written (tmp+move); issue flags are cleared exactly when the replacement transcript lands.

**Probe:** `OpenOats/Tests/OpenOatsTests/SessionRepositoryTests.swift:testSaveFinalTranscriptBacksUpLiveTranscriptWhenRequested` (:982–1007) — live-only session gains `transcript.pre-batch.jsonl` containing "Original live"; `testSaveFinalTranscriptBacksUpExistingFinalTranscriptWhenRequested` (:1009–1040) — second overwrite backs up the FINAL content ("Original final"), not the newer batch content; restore twins :1042–1083 pin both restore-success and missing-backup-false paths.

## Get live surrounding code
**Retrieve:** (executed live at pin; rank 1 = backup fn, rank 5 = saveFinalTranscript)
```ts
await mcp.codebase_memory.search_graph({ project: "openoats", query: "saveFinalTranscript backup transcript pre-batch overwrite tmp swap", limit: 10, fields: ["signature", "file"] });
// rank 1: backupTranscriptForBatchOverwrite :651-675; rank 2/4: restore tests;
// rank 3: hasPreBatchTranscriptBackup :1433-1441; rank 5: saveFinalTranscript :565-630
```

## Verdict
Adopt backup-before-destructive-write with empty-content suppression and tmp+move atomic swap; adopt the metadata recovery stamp so UI can badge recovered sessions. Adapt file names and the removeItem+moveItem pair to your platform's rename-replace primitive. Omit the mirror scheduling tail if you have no external notes destination.
