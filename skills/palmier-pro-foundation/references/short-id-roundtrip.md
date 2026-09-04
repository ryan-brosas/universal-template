<!-- capsule-v2 -->
# Short-id round-trip — how do 8-char ids shown to the model resolve back to full UUIDs safely?

**Source:** PalmierPro GPL-3.0 `main@49841f35b3eafa65c7eadc7b168bcc74db632906`; Codebase Memory `palmier-pro`. **Question:** What prefix length is safe to show an LLM, and what must happen when two ids share that prefix or the model echoes a prefix after ids changed?

## shortIdMap / expandingIdPrefixes / shorteningIds
**Path/Symbol:** `Sources/PalmierPro/Agent/Tools/ToolExecutor+ShortId.swift:ToolExecutor.shortIdMap` (67–78), `expandingIdPrefixes` (94–97), `shorteningIds` (55–64).
**Signature:** `nonisolated static func shortIdMap(_ ids: Set<String>) -> [String: String]`; `func expandingIdPrefixes(in args: [String: Any], editor: EditorViewModel) throws -> [String: Any]`.
**Data Shape:** internal ids are full UUIDs; wire-facing ids are prefixes with floor length 8 (`idPrefixFloor`); map is id → prefix.

### Decisive source
```swift
nonisolated static func shortIdMap(_ ids: Set<String>) -> [String: String] {
    let sorted = ids.sorted()
    var out: [String: String] = [:]
    for (i, id) in sorted.enumerated() {
        var sharedLen = 0
        if i > 0 { sharedLen = max(sharedLen, commonPrefixLength(id, sorted[i - 1])) }
        if i < sorted.count - 1 { sharedLen = max(sharedLen, commonPrefixLength(id, sorted[i + 1])) }
        let len = min(id.count, max(idPrefixFloor, sharedLen + 1))
        out[id] = String(id.prefix(len))
    }
    return out
}
```
Entry expansion resolves any prefix against the *current* editor id universe; exit shortening runs over **pre ∪ post** universes so ids created by this call and ids it just removed both resolve.

**Flow:** read tools serialize timelines through `shortIdMap(currentUniverse)` → model echoes a prefix in args → `expandingIdPrefixes` walks the arg tree and expands exact unique-prefix matches (ambiguous → throws ToolError "ambiguous"; unknown stays as-is and fails later as not-found) → tool mutates state → result payload passes through `shorteningIds(..., alsoKnown: idsBefore)` for re-shrinking.
**Invariant:** distinct ids always map to distinct prefixes even past an 8-char shared run; a prefix that matches two current ids never silently picks one.
**Probe:** `Tests/PalmierProTests/Agent/ShortIdTests.swift:58-65` (`prefixExtendsPastSharedRun`: shared 8-char run forces longer prefixes, `map[a] != map[b]`, count > 8), `:43-56` (`ambiguousPrefixIsRejected`: error contains "ambiguous"), `:13-21` (`emitsShortPrefixForFullUuid`: output contains prefix, never the full UUID).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "palmier-pro", query: "shortIdMap expandingIdPrefixes shorteningIds", limit: 10, fields: ["signature", "lines"] });
```

## Verdict
Adopt sorted-neighbor prefix computation with floor+1 extension and the ambiguous-prefix rejection. Adapt where the universe comes from (PalmierPro reads it from the live EditorViewModel before and after each call). Omit the timeline-specific serialization glue. Coverage: file `no_recorded_issue` @ gen 2026-08-25T19:59:55Z; ShortIdTests read directly.
