<!-- capsule-v2 -->
# JSONL tolerant repair — how do you fold late-arriving cleaned text into an append-only transcript without corrupting or losing lines?

**Source:** OpenOats MIT `main@bc0ddb9d5d12`; Codebase Memory `openoats`. **Question:** An LLM cleanup pass finishes AFTER the live JSONL was written — how do you backfill `cleanedText` into stored records while a crash mid-rewrite or a malformed line can never destroy the original transcript?

## Backup-first per-line merge with tolerant decode
**Path/Symbol:** `OpenOats/Sources/OpenOats/Storage/SessionRepository.swift:rewriteJSONLWithCleanedText` (:1846–1899); entry `backfillCleanedText` (:1500–1512); reader twin `parseJSONL` (:1806–1814); caller `finalizeSession` :437 (after handle close).
**Signature:** `@discardableResult private func rewriteJSONLWithCleanedText(file: URL, utterances: [Utterance]) -> Bool`; `func backfillCleanedText(sessionID: String, from utterances: [Utterance])`.
**Data Shape:** Returns whether any line changed; lookup key is `"ISO8601(withFractionalSeconds)|speaker.storageKey"` so a cleaned utterance matches exactly one record.

### Decisive source
```swift
let backupURL = file.appendingPathExtension("pre-cleanup.bak")
try? FileManager.default.copyItem(at: file, to: backupURL)   // backup BEFORE any mutation
...
for line in lines {
    guard let data = line.data(using: .utf8),
          var record = try? decoder.decode(SessionRecord.self, from: data) else {
        updatedLines.append(line)            // undecodable line passes through VERBATIM
        continue
    }
    if record.cleanedText == nil {           // only fill blanks — never overwrite
        let key = "\(iso8601Formatter.string(from: record.timestamp))|\(record.speaker.storageKey)"
        if let cleaned = cleanedLookup[key] {
            record = record.withCleanedText(cleaned)
            anyUpdated = true
        }
    }
    if let encoded = try? encoder.encode(record),
       let jsonString = String(data: encoded, encoding: .utf8) {
        updatedLines.append(jsonString)
    } else {
        updatedLines.append(line)            // re-encode failure keeps the original line
    }
}
if anyUpdated {
    try? newContent.write(to: file, atomically: true, encoding: .utf8)  // single atomic rewrite
}
```
Reader twin (`parseJSONL`, :1806–1814):
```swift
content.components(separatedBy: "\n").filter { !$0.isEmpty }
    .compactMap { line in ... try? decoder.decode(SessionRecord.self, from: data) }  // bad lines vanish silently
```

**Flow:** finalizeSession closes the live handle → backfillCleanedText picks canonical `transcript.live.jsonl` else legacy flat `<id>.jsonl` → rewrite makes a `.pre-cleanup.bak` copy → builds cleaned-text lookup keyed by timestamp|speaker → walks every line, decoding tolerantly, filling only nil-cleanedText records whose key matches → writes the whole file atomically only when at least one line changed. Loads use the same tolerance: empty lines dropped, undecodable lines silently skipped.
**Invariant:** The pre-existing transcript is recoverable at `<file>.pre-cleanup.bak` before any byte changes; a line is replaced only by a re-encoding of itself with `cleanedText` filled — no line is ever dropped or reordered, and already-cleaned lines are never touched. If nothing matched, the file is left byte-identical and the caller gets `false`.
**Probe:** No upstream XCTest exercises `rewriteJSONLWithCleanedText` directly (honest gap recorded this pass). The format contract it preserves is pinned by `SessionRepositoryTests.swift:testAppendLiveUtteranceWritesToJSONL` (:135–149, round-trips one appended utterance through loadTranscript), and the cleaned-text preference consumers rely on is pinned by `MarkdownMeetingWriterTests.testTranscriptLinePrefersCleanedText` (:130–142).

## Get live surrounding code
**Retrieve:** (executed live at pin)
```ts
await mcp.codebase_memory.search_graph({ project: "openoats", query: "backfillCleanedText rewrite JSONL cleaned text pre-cleanup backup tolerant decode", limit: 10, fields: ["signature","name","file"] });
// rank 1: rewriteJSONLWithCleanedText :1846-1899; rank 2: backfillCleanedText :1500-1512;
// rank 10: parseJSONL :1806-1814
```

## Verdict
Adopt backup-before-mutate + verbatim passthrough of undecodable/unchanged lines + atomic whole-file commit as the in-place repair contract for append-only logs. Adapt the match key (timestamp+speaker works because timestamps are ISO8601-normalized on write) to your record identity. Omit the legacy flat-file fallback only if your store has no migration history. Caveat: this seam has no direct upstream test — verify the .bak file exists after your port's first cleanup run.
