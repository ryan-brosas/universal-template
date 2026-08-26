<!-- capsule-v2 -->
# Abandoned-session resume election — which prior unfinished row may a restart resume instead of creating a duplicate?

**Source:** OpenOats MIT `main@bc0ddb9d5d12`; Codebase Memory `openoats`. **Question:** After a crash or quit, the same meeting is started again — when must the app reuse the previous empty row, and what disqualifies a row?

## Eligibility-filtered, gap-bounded, exact-event-first election
**Path/Symbol:** `OpenOats/Sources/OpenOats/Storage/SessionRepository.swift:resumableSessionID` (:1198–1241) + `resumeAbandonedSession` (:287–313); artifact predicate `sessionHasMeaningfulArtifacts` (:1280–1292).
**Signature:** `private func resumableSessionID(config: SessionStartConfig, maximumGap: TimeInterval) -> String?`; `@discardableResult func resumeAbandonedSession(config: SessionStartConfig, maximumGap: TimeInterval = 6 * 60 * 60) -> SessionHandle?`
**Data Shape:** Candidates are `(id, exactEventMatch: Bool, gap: TimeInterval)` tuples; sort = exact-event-match first, then smallest absolute gap. Default window 6 h anchored at `calendarEvent.startDate ?? Date()`.

### Decisive source
```swift
guard candidate.endedAt == nil,
      candidate.utteranceCount == 0,
      candidate.hasNotes == false,
      !sessionHasMeaningfulArtifacts(sessionID: candidate.id),
      let metadata = loadSessionMetadataFile(sessionID: candidate.id) else { return nil }
let gap = abs(metadata.startedAt.timeIntervalSince(referenceDate))
guard gap <= maximumGap else { return nil }
if let referenceEventID, metadata.calendarEvent?.id == referenceEventID {
    return (candidate.id, true, gap)          // exact event id beats title matching
}
guard MeetingHistoryResolver.historyKey(for: candidateTitle ?? "") == historyKey else { return nil }
return (candidate.id, false, gap)
```

**Flow:** compute reference title/history key + reference date → scan all sessions keeping only unfinished, empty, artifact-free rows within the gap → prefer exact calendar-event-id match over normalized-title match → smallest gap wins → `resumeAbandonedSession` re-points `currentSessionID`, reopens the live file handle (seek-to-end), and merges config title/calendar/templateSnapshot into the existing metadata.
**Invariant:** A row with ANY transcript content or meaningful artifacts can never be resumed into — it stays as history (the skips-rows-with-transcript-artifacts test asserts resume returns nil); resume mutates the existing row in place rather than creating a second session for the same meeting.

**Probe:** `OpenOats/Tests/OpenOatsTests/SessionRepositoryTests.swift:testResumeAbandonedSessionReusesEmptyUnfinishedMeetingRow` (:1174–1219) — resumed handle id equals the original, becomes current, and a post-resume utterance lands in that row's live transcript; `testResumeAbandonedSessionSkipsRowsWithTranscriptArtifacts` (:1221–1259) — row with one existing utterance → resume returns nil.

## Get live surrounding code
**Retrieve:** (executed live at pin)
```ts
await mcp.codebase_memory.search_graph({ project: "openoats", query: "resumableSessionID resume abandoned unfinished empty session election", limit: 10, fields: ["signature", "file"] });
// rank 1: reuse test :1174-1219; rank 2: resumeAbandonedSession :287-313;
// rank 3: skip test :1221-1259; rank 4: resumableSessionID :1198-1241
```

## Verdict
Adopt the four-part eligibility filter (unfinished ∧ 0 utterances ∧ no notes ∧ no artifacts), the abs-gap bound against the event start, and exact-event-id-over-title tie-breaking. Adapt the 6-hour default and the history-key normalizer to your identity model. Omit the metadata merge-on-resume only if your stubs already persist everything the new config would carry.
