<!-- capsule-v2 -->
# Imported/manual session creation — how do you create non-recorded session rows without duplicating the one a calendar event already owns?

**Source:** OpenOats MIT `main@bc0ddb9d5d12`; Codebase Memory `openoats`. **Question:** A user imports an audio file or starts typing a manual transcript for a meeting that may already have a stub row — how does OpenOats create these no-live-handle sessions and dedupe calendar-backed ones?

## Same-ID builder twins with 6h event/history-key reuse election
**Path/Symbol:** `OpenOats/Sources/OpenOats/Storage/SessionRepository.swift:createImportedSession` (:486–514), `createManualTranscriptSession` (:516–544), `existingSessionID` (:1243–1278), `finalizeImportedSession` (:547–552).
**Signature:** `@discardableResult func createImportedSession(config: ImportedSessionConfig) -> String`; `@discardableResult func createManualTranscriptSession(config: ManualTranscriptSessionConfig) -> String`; `private func existingSessionID(for event: CalendarEvent, referenceDate: Date, maximumGap: TimeInterval = 6 * 60 * 60) -> String?`.
**Data Shape:** Both builders RETURN the session id (existing or newly minted); neither opens a live file handle. Imported rows get an `audio/` dir and `source: "imported"`; manual rows get normalized `folderPath`, `source: "manual"`, and the calendarEvent.

### Decisive source
```swift
func createManualTranscriptSession(config: ManualTranscriptSessionConfig) -> String {
    if let existingSessionID = existingSessionID(for: config.calendarEvent, referenceDate: config.startedAt) {
        return existingSessionID                       // reuse beats creation — no second row
    }
    let formatter = DateFormatter()
    formatter.dateFormat = "yyyy-MM-dd_HH-mm-ss"
    let sessionID = "session_\(formatter.string(from: config.startedAt))"
    ...
}
// existingSessionID election:
if metadata.calendarEvent?.id == referenceEventID {
    return (candidate.id, true, gap)                   // exact event id ⇒ exact match
}
let candidateTitle = metadata.title ?? metadata.calendarEvent?.title
guard MeetingHistoryResolver.historyKey(for: candidateTitle ?? "") == historyKey else { return nil }
return (candidate.id, false, gap)
...
.sorted { lhs, rhs in
    if lhs.exactEventMatch != rhs.exactEventMatch {
        return lhs.exactEventMatch && !rhs.exactEventMatch   // exact always first
    }
    return lhs.gap < rhs.gap                               // then smallest |Δt|
}
```

**Flow:** manual create → consult existingSessionID (scan all sessions' metadata within a 6-hour absolute gap of the requested start; exact calendar-event-id match outranks normalized-title historyKey match; ties by smallest gap) → reuse returns the EXISTING id untouched → otherwise mint the timestamped id, mkdir, write metadata via the standard atomic+0600 path. Imported create skips the election entirely (an import is inherently a new artifact) but shares the same ID scheme, mkdir + audio/ subdir, and atomic metadata write; finalizeImportedSession later patches utteranceCount/endedAt in place.
**Invariant:** One calendar event can never own two manual-transcript rows inside the 6h window, and a recurring occurrence on another DAY fails the gap test so each occurrence gets its own row. The returned id is authoritative either way — callers must use it, never their requested config, to address the row afterward.
**Probe:** `OpenOats/Tests/OpenOatsTests/SessionRepositoryTests.swift:testCreateManualTranscriptSessionReusesExistingExactCalendarEvent` (:833–861, second create with shifted times returns the FIRST id; listSessions count == 1); `testCreateManualTranscriptSessionDoesNotReuseRecurringOccurrenceFromDifferentDay` (:863–907, same event id + next-day start yields TWO sessions); `testCreateManualTranscriptSessionPersistsCalendarFolderAndSource` (:811–831, source/folderPath/calendarEvent round-trip).

## Get live surrounding code
**Retrieve:** (executed live at pin)
```ts
await mcp.codebase_memory.search_graph({ project: "openoats", query: "createManualTranscriptSession reuse existing calendar event session id dedup imported", limit: 10, fields: ["signature","name","file"] });
// rank 1: testCreateManualTranscriptSessionReusesExistingExactCalendarEvent :833-861;
// rank 2: createManualTranscriptSession :516-544; rank 4: existingSessionID :1243-1278;
// rank 8-9: createImportedSession :486-514 / finalizeImportedSession :547-552
```

## Verdict
Adopt the two-tier election (exact external id > normalized title key, both gap-bounded) for any "create-or-attach" flow over durable rows, and the return-the-authoritative-id contract. Adapt the 6-hour maximumGap and the history-key normalization to your domain's recurrence semantics. Omit the imported-twin builder if your store has no bulk-import entry point — but keep handle-less creation separate from startSession so imports never inherit live-append state.
