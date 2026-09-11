<!-- capsule-v2 -->
# Ghost-session reconciliation — when does an empty calendar-bearing session merge into a real one instead of lingering?

**Source:** OpenOats MIT `main@bc0ddb9d5d12`; Codebase Memory `openoats`. **Question:** A meeting was auto-stubbed (calendar event attached) but recorded nothing — should the stub be deleted, and where does its calendar context go?

## Merge-into-nearest-real-then-delete
**Path/Symbol:** `OpenOats/Sources/OpenOats/Storage/SessionRepository.swift:reconcileGhostSession` (:1085–1124); artifact predicate `sessionHasMeaningfulArtifacts` (:1280–1292); history key `MeetingHistoryResolver.historyKey`.
**Signature:** `func reconcileGhostSession(sessionID: String, maximumGap: TimeInterval = 5 * 60) -> String?`
**Data Shape:** Returns the surviving real session id when a merge happened; nil when the row is not reconcilable (has content, no calendar event, empty history key, or no candidate within gap).

### Decisive source
```swift
guard let ghostMeta = loadSessionMetadataFile(sessionID: sessionID),
      ghostMeta.utteranceCount == 0,
      ghostMeta.hasNotes == false,
      let calendarEvent = ghostMeta.calendarEvent,
      !sessionHasMeaningfulArtifacts(sessionID: sessionID) else { return nil }
let historyKey = MeetingHistoryResolver.historyKey(for: ghostMeta.title ?? calendarEvent.title)
guard !historyKey.isEmpty else { return nil }
let candidates = listSessions().filter { candidate in
    guard candidate.id != sessionID, candidate.utteranceCount > 0,
          MeetingHistoryResolver.historyKey(for: candidate.title ?? "") == historyKey
    else { return false }
    let gap = ghostMeta.startedAt.timeIntervalSince(candidate.endedAt ?? candidate.startedAt)
    return gap >= 0 && gap <= maximumGap        // ghost started AFTER the real one ended
}.sorted { lhsGap < rhsGap }                    // nearest predecessor wins
guard let target = candidates.first else { return nil }
if let targetMeta = ..., targetMeta.calendarEvent == nil {
    updateSessionCalendarEvent(sessionID: target.id, calendarEvent: calendarEvent)
}
deleteSession(sessionID: sessionID)
return target.id
```

**Flow:** qualify ghost (0 utterances ∧ no notes ∧ has calendarEvent ∧ no meaningful artifacts) → compute normalized title history key → filter same-key real sessions that ENDED before the ghost started within `maximumGap` → pick smallest gap → back-fill calendar event onto the target only if it lacks one → delete ghost → return target id.
**Invariant:** A session with any transcript/notes/audio artifacts is never treated as a ghost (the audio-artifact test pins this); calendar context moves at most once (only into a target with nil calendarEvent); the ghost's own start must follow the real session's end (gap ≥ 0), so an unrelated earlier meeting never absorbs it.

**Probe:** `OpenOats/Tests/OpenOatsTests/SessionRepositoryTests.swift:testReconcileGhostSessionMergesCalendarEventIntoRecentRealSession` (:1085–1124) asserts merged id == "session_real", single remaining "Customer Sync" row, and target carries the ghost's calendarEvent id; `testReconcileGhostSessionKeepsEmptySessionWhenAudioArtifactsExist` (:1126–1172) asserts an empty-but-audio-bearing session survives.

## Get live surrounding code
**Retrieve:** (executed live at pin)
```ts
await mcp.codebase_memory.search_graph({ project: "openoats", query: "reconcileGhostSession merge calendar event into recent real session", limit: 10, fields: ["signature", "file"] });
// rank 1: the merge test :1085-1124; rank 3: reconcileGhostSession :1085-1124;
// rank 4: updateSessionCalendarEvent :1053-1083
```

## Verdict
Adopt the five-part ghost predicate plus forward-gap candidate filter as the safe merge contract. Adapt the 5-minute gap, the history-key normalization, and the "target lacks calendar" fill rule to your domain. Omit deletion-on-merge if your product prefers tombstones — but keep the returned survivor id so callers can redirect UI.
