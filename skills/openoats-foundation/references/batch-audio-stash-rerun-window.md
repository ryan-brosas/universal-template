<!-- capsule-v2 -->
# Batch audio stash & rerun window — how are batch audio stems retained for reruns yet garbage-collected?

**Source:** OpenOats MIT `main@bc0ddb9d5d12`; Codebase Memory `openoats`. **Question:** Where do batch-transcription audio stems and timing anchors live, how long must they survive, and when exactly are they deleted?

## Stash-now, sweep-at-init, 7-day window
**Path/Symbol:** `OpenOats/Sources/OpenOats/Storage/SessionRepository.swift:stashAudioForBatch` (:1373–1402), `cleanupExpiredRetainedBatchAudio` (:2101–2141), constant :180; call site `init` (:230).
**Signature:** `func stashAudioForBatch(sessionID: String, micURL: URL?, sysURL: URL?, anchors: BatchAnchors)`; `private static func cleanupExpiredRetainedBatchAudio(in sessionsDirectory: URL)`; `retainedBatchAudioLifetime: TimeInterval = 7 * 24 * 3600`.
**Data Shape:** Moves source recordings into `sessions/<id>/audio/{mic.caf,sys.caf}` and writes `audio/batch-meta.json` (mic/sys start dates, per-frame time anchors, effective system sample rate) atomically via a shared ISO8601 encoder.

### Decisive source
```swift
let cutoff = Date().addingTimeInterval(-retainedBatchAudioLifetime)
for item in contents {
    guard ..., values.isDirectory == true else { continue }
    guard name.hasPrefix("session_") else { continue }
    let audioDir = item.appendingPathComponent("audio", isDirectory: true)   // canonical
    let micLegacy = item.appendingPathComponent("mic.caf")                   // legacy flat layout
    /* hasAudio checks canonical AND legacy paths */
    if let modDate = values.contentModificationDate, modDate < cutoff {
        try? fm.removeItem(at: micCanonical); ... try? fm.removeItem(at: sysLegacy)
        Log.sessionRepository.info("Cleaned up expired retained batch audio in \(name)")
    }
}
```
called from `init`: `Self.cleanupExpiredRetainedBatchAudio(in: sessionsDirectory)` — retention is enforced at repository construction, not on a timer.

**Flow:** batch transcription seals recordings → stash moves them into the session's audio/ dir + atomic anchors file → later repository initializations sweep session dirs whose modification date is older than the 7-day cutoff → delete stems + batch-meta.json across canonical and legacy layouts.
**Invariant:** Stems survive at least the rerun window so "re-run batch transcription" stays possible after restart/app-update; cleanup keys off the SESSION DIRECTORY's contentModificationDate (any write refreshes it), never off file mtimes inside; deletion is fail-soft per-file.

**Probe:** `OpenOats/Tests/OpenOatsTests/SessionRepositoryTests.swift:testInitRetainsRecentBatchAudioForRerunWindow` (:1319–1334) — dir mtime −6 days → fresh repo still returns mic/sys URLs + meta; `testInitCleansExpiredBatchAudioAfterRerunWindow` (:1336–1351) — mtime −8 days → all nil after init.

## Get live surrounding code
**Retrieve:** (executed live at pin)
```ts
await mcp.codebase_memory.search_graph({ project: "openoats", query: "stashAudioForBatch retained batch audio rerun window cleanup", limit: 10, fields: ["signature", "file"] });
// rank 1: cleanupExpiredRetainedBatchAudio :2101-2141; rank 2: stashAudioForBatch :1373-1402;
// rank 3/4: the two init-window tests
```

## Verdict
Adopt move-into-place stashing with sidecar anchor metadata and an init-time, directory-mtime-keyed retention sweep. Adapt the 7-day constant to your product's rerun expectations and the CAF filenames to your codec. Omit the legacy-layout probing only if your storage never shipped an older layout.
