<!-- capsule-v2 -->
# Anthropic SSE fold — how does a raw Anthropic SSE byte stream fold into provider-neutral events?

**Source:** PalmierPro GPL-3.0 `main@49841f35b3eafa65c7eadc7b168bcc74db632906`; Codebase Memory `palmier-pro`. **Question:** Where must tool_use input JSON be buffered during streaming, and what happens to a tool call whose input arrives as zero delta bytes?

## AnthropicSSE.parse
**Path/Symbol:** `Sources/PalmierPro/Agent/Clients/AnthropicProvider.swift:AnthropicSSE.parse` (17–92).
**Signature:** `static func parse(bytes: URLSession.AsyncBytes, continuation: AsyncThrowingStream<AgentStreamEvent, Error>.Continuation) async throws`.
**Data Shape:** in: SSE lines; state: `pendingTools: [Int: (id: String, name: String, json: String)]` keyed by content-block index; out: neutral `.textDelta/.thinkingDelta/.thinkingSignature/.redactedThinking/.toolUseComplete(id, name, inputJSON)/.messageStop`.

### Decisive source
```swift
case "content_block_delta":
    ...
    } else if deltaType == "input_json_delta",
              let partial = delta["partial_json"] as? String,
              var acc = pendingTools[index] {
        acc.json += partial
        pendingTools[index] = acc
    }

case "content_block_stop":
    if let index = event["index"] as? Int, let acc = pendingTools.removeValue(forKey: index) {
        let json = acc.json.isEmpty ? "{}" : acc.json     // zero-delta tool call still completes
        continuation.yield(.toolUseComplete(id: acc.id, name: acc.name, inputJSON: json))
    }
```
Termination and error mapping:
```swift
case "message_delta":
    if let raw = delta["stop_reason"] as? String {
        continuation.yield(.messageStop(stopReason: AgentStopReason(rawValue: raw) ?? .other))
    }
case "error":
    throw AgentClientTransportError.streamError(provider: .anthropic, message: msg)
```

**Flow:** per line: cancellation check → accept only `data:` prefixed lines → JSON-parse (malformed lines silently skipped, not fatal) → route by `type`: message_start records usage; content_block_start registers tool_use slots or yields redacted thinking; content_block_delta routes text/thinking/signature deltas or accumulates partial tool JSON by block index; content_block_stop flushes the accumulated JSON as one `.toolUseComplete`; message_delta maps stop_reason with unknown→`.other`; error events *throw*.
**Invariant:** a tool call is emitted exactly once, at `content_block_stop`, with syntactically valid JSON even when the model sent no input deltas (`"{}"`); unknown stop reasons degrade to `.other` rather than crashing the loop.
**Probe:** `Tests/PalmierProTests/Agent/AgentStreamPresentationTests.swift` exercises the downstream fold of `.toolUseComplete`; no dedicated AnthropicSSE unit test exists upstream — parser verified from source only (recorded caveat).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "palmier-pro", query: "AnthropicSSE parse pendingTools content_block_stop", limit: 10, fields: ["signature", "lines"] });
```

## Verdict
Adopt the index-keyed accumulation dict and the empty→`{}` completion rule; adopt unknown-stop-reason → `.other` and throw-on-error-event. Adapt the transport (`URLSession.AsyncBytes.lines`) to your HTTP stack. Omit the PalmierPro usage-log side channel (`AgentUsageLog.record`). The OpenAI twin (`OpenAISSE.parse`, 133–145+) is a separate pass — do not assume symmetry. Coverage: file `no_recorded_issue` @ gen 2026-08-25T19:59:55Z.
