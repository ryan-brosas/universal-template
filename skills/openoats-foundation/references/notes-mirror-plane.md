<!-- capsule-v2 -->
# Notes mirror plane — how do you export session notes to a user-chosen folder without blocking the actor or following malicious markdown links?

**Source:** OpenOats MIT `main@bc0ddb9d5d12`; Codebase Memory `openoats`. **Question:** A porter must copy finalized notes (+ any images/attachments they reference) into an external "notes folder" — how does OpenOats keep this off the storage actor, honor macOS security-scoped folders, and refuse path-traversal link targets?

## Snapshot-then-detached mirror with traversal-guarded asset package
**Path/Symbol:** `OpenOats/Sources/OpenOats/Storage/SessionRepository.swift:scheduleMirror` (:1909–1926) → `performMirror` (:1928–1987) → `mirrorDirectory` (:1989–1996), `referencedMirrorAssetPaths` (:1998–2016), `normalizedMirrorAssetPath` (:2018–2052), `synchronizeMirroredAssets` (:2054–2088).
**Signature:** `private func scheduleMirror(sessionID: String, notesMarkdown: String? = nil)`; `private nonisolated static func performMirror(sessionID:meta:notesMarkdown:outputDir:isSecurityScoped:dateSubfolderFormat:sessionsDirectory:)`.
**Data Shape:** scheduleMirror returns immediately after spawning; all actor state is captured as values BEFORE `Task.detached(priority: .background)`. performMirror returns Void and silently no-ops on empty transcripts or nil output targets.

### Decisive source
```swift
private func scheduleMirror(sessionID: String, notesMarkdown: String? = nil) {
    guard let outputDir = notesFolderPath else { return }
    let sessDir = sessionsDirectory
    let isSecurityScoped = notesFolderIsSecurityScoped
    let dateSubfolderFormat = meetingTranscriptDateFolderFormat
    let meta = loadSessionMetadataFile(sessionID: sessionID)
    Task.detached(priority: .background) {
        SessionRepository.performMirror(..., outputDir: outputDir, isSecurityScoped: isSecurityScoped, ...)
    }
}
// performMirror:
let didStartAccess = isSecurityScoped && outputDir.startAccessingSecurityScopedResource()
defer { if didStartAccess { outputDir.stopAccessingSecurityScopedResource() } }
let records = readTranscript(...)
guard !records.isEmpty else { return }              // empty transcript ⇒ nothing mirrored
...
preferPackage: !referencedAssetPaths.isEmpty        // links present ⇒ package dir, not flat file
```
Guard excerpt from `normalizedMirrorAssetPath` (:2034–2049):
```swift
guard !target.isEmpty,
      !target.hasPrefix("/"),          // absolute paths rejected
      !target.hasPrefix("~"),          // home-relative rejected
      URL(string: target)?.scheme == nil else {   // http(s)/file URLs rejected
    return nil
}
let components = target.split(separator: "/", omittingEmptySubsequences: true).map(String.init)
guard let first = components.first,
      first == "attachments" || first == "images",   // allow-list of session-local dirs
      !components.contains(".."),
      !components.contains(".") else {
    return nil
}
```

**Flow:** caller (saveNotes/saveFinalTranscript/finalizeSession/renameSession/updateSessionCalendarEvent) → scheduleMirror snapshots metadata + config → detached background task → security-scope bracket (deferred stop) → read transcript (empty ⇒ abort) → resolve markdown (argument wins over disk re-read) → extract link/image targets → normalize each through the traversal guard into a Set → build SessionIndex (`meetingFamilyKey = calendarEvent.flatMap { MeetingHistoryResolver.seriesHistoryKey(for:) }`) → `MarkdownMeetingWriter.write(outputDirectory: mirrorDirectory(...), preferPackage:)` → if a package was produced, wipe destination `attachments/`+`images/`, then sorted copy-in of existing sources only, chmod 0600 each.
**Invariant:** The mirror never runs on the actor (all inputs are value-captured first), never mirrors a session with zero transcript records, and only ever copies files whose normalized relative path starts with `attachments/` or `images/` with no `..`/`.` components — a note cannot make OpenOats copy arbitrary filesystem paths. Date-subfolder routing happens only when the format is configured (`mirrorDirectory` returns the root otherwise).
**Probe:** `OpenOats/Tests/OpenOatsTests/SessionRepositoryTests.swift:testSaveNotesMirrorsToNotesFolderPath` (:352–391, polls for the detached task's `<title>.md`); `testSaveNotesMirrorsIntoISODateSubfolder` (:393–442, asserts md lands in `2026-05-02/` AND top level has no md); `testSaveNotesMirrorsReferencedAssetsIntoPackageDirectory` (:444–512, asserts notes.md + attachment + image exist inside one package directory and no flat md twin exists).

## Get live surrounding code
**Retrieve:** (executed live at pin)
```ts
await mcp.codebase_memory.search_graph({ project: "openoats", query: "scheduleMirror performMirror mirror notes folder security scoped package assets", limit: 10, fields: ["signature","name","file"] });
// rank 1: scheduleMirror :1909-1926; rank 2: performMirror :1928-1987;
// rank 3: testSaveNotesMirrorsReferencedAssetsIntoPackageDirectory :444-512;
// ranks 5-7+10: mirrorDirectory / referencedMirrorAssetPaths / normalizedMirrorAssetPath / synchronizeMirroredAssets
```

## Verdict
Adopt the snapshot-then-detach pattern for off-actor export work and the allow-list + component-normalization link guard before copying any note-referenced asset. Adapt the destination layout (date subfolders, package-vs-flat choice) and the security-scoped bracket to your host's sandbox model. Omit MarkdownMeetingWriter internals if you render notes differently — but keep "empty transcript ⇒ no mirror" so stub sessions never pollute the user's notes folder. Coverage: SessionRepository.swift + SessionRepositoryTests.swift were no_recorded_issue/metadata_match at gen 2026-08-25T19:59:34Z.
