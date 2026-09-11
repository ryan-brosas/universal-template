<!-- capsule-v2 -->
# Attachment import + plaintext export — how do you import user files into a session store without letting hostile filenames or failed copies corrupt metadata?

**Source:** OpenOats MIT `main@bc0ddb9d5d12`; Codebase Memory `openoats`. **Question:** A porter must let users attach arbitrary files to a session and later export the transcript as plain text — how does OpenOats keep stored filenames safe, keep metadata consistent when the copy fails, and render cleaned-over-raw text?

## UUID-prefixed sanitized storage name + copy-before-metadata + cleanedText-first export
**Path/Symbol:** `OpenOats/Sources/OpenOats/Storage/SessionRepository.swift:importAttachment` (:722–774), `sanitizedAttachmentFilename` (:1795–1804), `saveImage` (:813–821), `exportPlainText` (:1348–1369).
**Signature:** `func importAttachment(sessionID: String, sourceURL: URL) -> NoteAttachment?`; `private nonisolated static func sanitizedAttachmentFilename(_ value: String) -> String`; `func saveImage(sessionID: String, imageData: Data) -> String`; `func exportPlainText(sessionID: String) -> String`.
**Data Shape:** importAttachment returns nil on copy failure (no metadata mutation); on success returns the NoteAttachment whose `displayName` is the ORIGINAL filename verbatim while `relativePath` is `attachments/<UUID>-<sanitizedBaseName>[.ext]`. Extension is taken from the source URL by trimming whitespace only — there is no extension whitelist.

### Decisive source
```swift
let sanitizedBaseName = Self.sanitizedAttachmentFilename(sourceURL.deletingPathExtension().lastPathComponent)
let pathExtension = sourceURL.pathExtension.trimmingCharacters(in: .whitespacesAndNewlines)
let storedFilename: String
if pathExtension.isEmpty {
    storedFilename = "\(UUID().uuidString)-\(sanitizedBaseName)"
} else {
    storedFilename = "\(UUID().uuidString)-\(sanitizedBaseName).\(pathExtension)"
}
...
do {
    try FileManager.default.copyItem(at: sourceURL, to: destinationURL)
} catch {
    Log.sessionRepository.error("Failed to import attachment: \(error, privacy: .public)")
    return nil                       // copy failed ⇒ NO metadata append happens
}
try? FileManager.default.setAttributes([.posixPermissions: 0o600], ofItemAtPath: destinationURL.path)
```
Sanitizer (:1795–1803):
```swift
let allowed = CharacterSet.alphanumerics.union(.init(charactersIn: "-_"))
let scalars = value.unicodeScalars.map { scalar -> Character in
    allowed.contains(scalar) ? Character(scalar) : "-"
}
let raw = String(scalars)
    .replacingOccurrences(of: "--+", with: "-", options: .regularExpression)
    .trimmingCharacters(in: CharacterSet(charactersIn: "-"))
return raw.isEmpty ? "attachment" : raw
```
Export (:1357–1368):
```swift
for record in records {
    let displayText = record.cleanedText ?? record.text
    result += "[\(timeFmt.string(from: record.timestamp))] \(record.speaker.displayLabel): \(displayText)\n"
}
```

**Flow:** ensure `attachments/` dir → sanitize base name (hostile chars → `-`, collapse runs, trim edge dashes, empty ⇒ "attachment") → compose `<UUID>-<name>[.ext]` → copy; failure logs and returns nil BEFORE any meta write → chmod 0600 → contentType from resourceValues else UTType-by-extension fallback → byteSize → append NoteAttachment(displayName=original) to notes.meta.json attachments (missing meta ⇒ fallback "Generic" template snapshot + fresh generatedAt) → return attachment. Export: load transcript (empty ⇒ ""), header `OpenOats - <medium date>` from metadata.startedAt ?? first record timestamp, then one `[HH:mm:ss] <displayLabel>: <cleanedText ?? text>` line per record.
**Invariant:** The on-disk name is always `<UUID>-<safe>[.ext]` (no path separators, no leading dash, unique per import) while the user-visible displayName is never rewritten; a failed copy never appends metadata (no dangling relativePath); every stored file is 0600; export prefers cleanedText but never drops a line that only has raw text.
**Probe:** `OpenOats/Tests/OpenOatsTests/SessionRepositoryTests.swift:testImportAttachmentPersistsMetadataAndFile` (:514–544, "Quarterly Plan.pdf" keeps its displayName, file exists at the returned relativePath, detail.attachments has 1 entry); `testSaveNotesPreservesExistingAttachments` (:546–572, saveNotes does not clobber the imported attachment list); `testExportPlainText` (:769–788, header contains "OpenOats", lines contain "You: Hello there" / "Them: Hi back").

## Get live surrounding code
**Retrieve:** (executed live at pin; Codebase Memory MCP not connected this session — direct source+test read fallback)
```bash
sed -n '722,774p' OpenOats/Sources/OpenOats/Storage/SessionRepository.swift   # importAttachment body
sed -n '1795,1804p' OpenOats/Sources/OpenOats/Storage/SessionRepository.swift # sanitizer
sed -n '1348,1369p' OpenOats/Sources/OpenOats/Storage/SessionRepository.swift # exportPlainText
sed -n '514,572p;769,788p' OpenOats/Tests/OpenOatsTests/SessionRepositoryTests.swift
```

## Verdict
Adopt the three-part contract: (1) store under a UUID-prefixed sanitized name while keeping the original display name in metadata, (2) perform the byte copy FIRST and only touch metadata after success so failures leave zero trace, (3) render `cleaned ?? raw` per line for exports. Adapt the sanitizer's allowed set and the 0600 hardening to your host's permission model; omit the UTType/resourceValues content-type detection if your host has no equivalent. Coverage caveat: MCP graph not connected this pass; all ranges read directly at pin bc0ddb9d.
