<!-- capsule-v2 -->
# Tool arg decode, no-trap — how are LLM-supplied arguments decoded without trapping on overflow or unknown keys?

**Source:** PalmierPro GPL-3.0 `main@49841f35b3eafa65c7eadc7b168bcc74db632906`; Codebase Memory `palmier-pro`. **Question:** How do you turn hostile `[String: Any]` tool args (huge JSON numbers, unknown keys, blank strings) into typed values without ever crashing the host?

## decodeToolArgs + safeInt/clampInt + droppingAutofilledBlanks
**Path/Symbol:** `Sources/PalmierPro/Agent/Tools/ToolExecutor.swift:decodeToolArgs` (460–475) with `DecodableToolArgs` (456–458); numeric guards + `ToolExecutor.droppingAutofilledBlanks` (same file); `Dictionary.int` helper consumed at use sites.
**Signature:** `func decodeToolArgs<T: DecodableToolArgs>(_ dict: [String: Any], path: String) throws -> T`.
**Data Shape:** in: raw `[String: Any]` from JSONSerialization; out: typed args struct or `ToolError` with a path-prefixed message.

### Decisive source
```swift
func decodeToolArgs<T: DecodableToolArgs>(_ dict: [String: Any], path: String) throws -> T {
    try validateUnknownKeys(dict, allowed: T.allowedKeys, path: path)
    if let badPath = firstNonFiniteNumberPath(in: dict, path: path) {
        throw ToolError("\(badPath): value must be finite")
    }
    let data = try JSONSerialization.data(withJSONObject: dict)
    do { return try JSONDecoder().decode(T.self, from: data) }
    catch let e as DecodingError { throw ToolError(formatDecodingError(e, path: path)) }
}
```
The no-trap contract (born from a live crash — see the test comment "Exactly the JSON that crashed the live app via the MCP socket"):
```swift
let json = #"{"startFrame": 1e19}"#.data(using: .utf8)!
let args = try JSONSerialization.jsonObject(with: json) as? [String: Any]
#expect(args.int("startFrame") == nil)        // was: hard crash via Int(Double).trap
```

**Flow:** validate unknown keys against the per-type `allowedKeys` → reject NaN/±inf/overflow doubles by path → re-serialize to JSON → `JSONDecoder` into the typed struct → decoding errors reformatted as `"<path>: <reason>"` ToolErrors. Separately, `droppingAutofilledBlanks` removes `""` / `NSNull` optional params before dispatch so OpenAI-style autofill never becomes an id lookup.
**Invariant:** no Double→Int conversion in the tool plane may trap; every rejection names its arg path; omitted and blank-filled optionals behave identically.
**Probe:** `Tests/PalmierProTests/Agent/ToolArgOverflowTests.swift:9-20` (`safeIntRejectsOverflowAndNonFinite`: 1e19, ±inf, NaN → nil; 3.9 truncates toward zero), `:31-36` (the exact crash repro), `:53-60` (`getTimelineSurvivesHugeStartFrame` end-to-end returns a timeline, `isError == false`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "palmier-pro", query: "decodeToolArgs validateUnknownKeys safeInt", limit: 10, fields: ["signature", "lines"] });
```

## Verdict
Adopt all three layers: allowedKeys validation, finite-number pre-check, and trap-free numeric coercion helpers (`safeInt`, `clampInt` clamps instead of rejecting when a bounded value is legal). Adapt error-message wording to your protocol. Omit nothing here — this is the most directly portable seam in the repo. Coverage: ToolExecutor.swift `no_recorded_issue` @ gen 2026-08-25T19:59:55Z; overflow tests read directly.
