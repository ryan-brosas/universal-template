<!-- capsule-v2 -->
# Session canonical layout & seeding — what exactly must a new session persist, and with which durability/permission guarantees?

**Source:** OpenOats MIT `main@bc0ddb9d5d12`; Codebase Memory `openoats`. **Question:** When creating a session record from scratch (fixture or batch seed), which files must exist before the session is listable, and how are they written safely?

## Canonical per-session directory contract
**Path/Symbol:** `OpenOats/Sources/OpenOats/Storage/SessionRepository.swift:seedSession` (:1516–1562) + `writeSessionMetadata` (:1760–1775); layout doc comment :168–177.
**Signature:** `func seedSession(id: String, records: [SessionRecord], startedAt: Date, endedAt: Date? = nil, templateSnapshot: TemplateSnapshot? = nil, title: String? = nil, notes: GeneratedNotes? = nil, transcriptIssue: SessionTranscriptIssue? = nil, transcriptRecovery: SessionTranscriptRecoveryState? = nil)`
**Data Shape:** Inputs: session id (timestamp string `session_yyyy-MM-dd_HH-mm-ss` produced by `startSession` :261–264), ordered JSONL records, metadata fields. Output: directory `sessions/<id>/` containing `session.json`, `transcript.live.jsonl`, optional notes; no return value (fail-soft `try?`). The actor owns one shared ISO8601 encoder (:221–222).

### Decisive source
```swift
let meta = SessionMetadata(id: id, startedAt: startedAt, ..., utteranceCount: records.count,
                           hasNotes: notes != nil, ...)
writeSessionMetadata(meta, sessionID: id)

let liveURL = dir.appendingPathComponent("transcript.live.jsonl")
var payload = Data()
for record in records {
    if let data = try? encoder.encode(record) { payload.append(data); payload.append(Data("\n".utf8)) }
}
try? payload.write(to: liveURL, options: .atomic)
try? FileManager.default.setAttributes([.posixPermissions: 0o600], ofItemAtPath: liveURL.path)
```
and in `writeSessionMetadata`: `enc.outputFormatting = [.prettyPrinted, .sortedKeys]` → `data.write(to: url, options: .atomic)` → chmod 0600.

**Flow:** mkdir -p session dir → write session.json (pretty+sorted keys, atomic, 0600) → buffer all records into one payload with `\n` delimiters → single atomic write of transcript.live.jsonl → chmod 0600 → optionally `saveNotes`.
**Invariant:** A seeded session is complete after one atomic write per file — readers never observe a half-written transcript; both persisted files carry owner-only POSIX permissions; `utteranceCount` in metadata always equals `records.count`.

**Probe:** `OpenOats/Tests/OpenOatsTests/SessionRepositoryTests.swift:testStartSessionCreatesDirectoryLayout` (:54–71) pins that `startSession` produces the exact canonical file set; `testStartSessionPersistsRecurringMeetingFamilyKey` (:103–131) pins identity persistence through metadata.

## Get live surrounding code
**Retrieve:** (executed live at pin; top hit = target)
```ts
await mcp.codebase_memory.search_graph({ project: "openoats", query: "seedSession writes canonical session directory layout", limit: 10, fields: ["signature", "file"] });
// → rank 3: …Storage.SessionRepository.seedSession (SessionRepository.swift 1516-1562);
//   rank 1: test fixture testStartSessionCreatesDirectoryLayout :54-71
```

## Verdict
Adopt the atomic-write-then-chmod pairing, single-buffer JSONL seeding, and timestamp-derived ids as the portability core. Adapt the ISO8601/prettyPrinted encoder settings to your serializer's equivalent deterministic form. Omit the `try?` fail-soft posture if your host can surface write errors (OpenOats routes them to an optional once-per-session error handler instead).
