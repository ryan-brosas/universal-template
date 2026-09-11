<!-- capsule-v2 -->
# Internal-tag-preserving tag update — how do user tag edits avoid destroying importer-namespaced tags?

**Source:** OpenOats MIT `main@bc0ddb9d5d12`; Codebase Memory `openoats`. **Question:** The UI hands the store a plain list of user tags — what keeps machine-written namespaced tags (importer bookkeeping) from being wiped by that write?

## Split-preserve-prepend update
**Path/Symbol:** `OpenOats/Sources/OpenOats/Storage/SessionRepository.swift:updateSessionTags` (:981–1014), `internalSessionTags(from:)` (:1190–1192), `isInternalSessionTag` (:1294–1296), normalizers :1154–1184.
**Signature:** `func updateSessionTags(sessionID: String, tags: [String])`; helpers `static func internalSessionTags(from tags: [String]) -> [String]`, `private static func isInternalSessionTag(_ tag: String) -> Bool`.
**Data Shape:** One `tags: [String]?` field in session.json holding BOTH families, ordered internal-first; user input is normalized (dedupe/trim) before combining; empty combined list persists as `nil`.

### Decisive source
```swift
let normalizedVisibleTags = Self.normalizeUserVisibleTags(tags)
if var meta = loadSessionMetadataFile(sessionID: sessionID) {
    let preservedInternalTags = Self.internalSessionTags(from: meta.tags ?? [])
    let combinedTags = preservedInternalTags + normalizedVisibleTags
    meta.tags = combinedTags.isEmpty ? nil : combinedTags
    writeSessionMetadata(meta, sessionID: sessionID)
    return
}
// legacy fallback: build a fresh SessionMetadata from LegacySessionReader.loadIndex(...)
// and write it — first tag write migrates the session to canonical format.
```

**Flow:** normalize incoming user tags → load canonical metadata → filter existing tags down to internal ones → persist internals PREPENDED to normalized user tags → done. If no canonical session.json exists (legacy layout), reconstruct full metadata from the legacy index and write it canonically as a side-effect of the first tag edit.
**Invariant:** User-visible tag writes are total for the user namespace but partial for the whole field: anything matching the internal predicate survives unchanged and keeps its leading position; an all-empty result collapses to nil rather than an empty array.

**Probe:** `OpenOats/Tests/OpenOatsTests/SessionRepositoryTests.swift:testUpdateSessionTagsPreservesInternalGranolaTag` (:1295–1317) — after `updateSessionSource(source: "granola", tags: ["granola:not_123"])` then `updateSessionTags(tags: ["team","follow-up"])`, saved tags equal exactly `["granola:not_123","team","follow-up"]`.

## Get live surrounding code
**Retrieve:** (executed live at pin)
```ts
await mcp.codebase_memory.search_graph({ project: "openoats", query: "updateSessionTags preserves internal granola tag", limit: 10, fields: ["signature", "file"] });
// rank 1: testUpdateSessionTagsPreservesInternalGranolaTag :1295-1317;
// rank 2: isInternalSessionTag :1294-1296; rank 3: updateSessionTags :981-1014;
// rank 5: internalSessionTags :1190-1192
```

## Verdict
Adopt namespaced-tag preservation with internal-before-visible ordering on every user-driven rewrite of the shared field. Adapt the predicate (OpenOats uses the `granola:` prefix family) to your importer namespaces. Omit the legacy migration branch if your store never shipped a pre-canonical format — but keep it in mind as the pattern for schema migrations piggybacked on ordinary writes.
