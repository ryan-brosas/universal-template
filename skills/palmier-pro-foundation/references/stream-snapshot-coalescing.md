<!-- capsule-v2 -->
# Stream snapshot coalescing — how do token deltas become UI snapshots without flooding the main actor?

**Source:** PalmierPro GPL-3.0 `main@49841f35b3eafa65c7eadc7b168bcc74db632906`; Codebase Memory `palmier-pro`. **Question:** What is the publish schedule and fold rule that turns an unbounded delta stream into a bounded number of conversation updates?

## AgentStreamReducer + AgentStreamPresentationBuffer
**Path/Symbol:** `Sources/PalmierPro/Agent/Chat/AgentStreamPresentationBuffer.swift:AgentStreamReducer` (10–79), `AgentStreamPresentationBuffer` (81–165).
**Signature:** `private struct AgentStreamReducer: Sendable { mutating func apply(_ event: AgentStreamEvent) -> Bool }`; `actor AgentStreamPresentationBuffer { func receive(_ event: AgentStreamEvent); func complete(throwing:) -> AgentStreamSnapshot; func snapshots() -> AsyncThrowingStream<AgentStreamSnapshot, Error> }`.
**Data Shape:** in: `AgentStreamEvent` deltas; out: `AgentStreamSnapshot { blocks: [AgentContentBlock], stopReason, revision: UInt64 }`; snapshot stream uses `.bufferingNewest(1)`.

### Decisive source
```swift
func receive(_ event: AgentStreamEvent) {
    guard !isComplete else { return }
    guard reducer.apply(event) else { return }   // messageStop returns false
    revision &+= 1
    isDirty = true
    if !hasPublished { publish() }               // first event: immediate
    scheduleIfNeeded()                           // else 50 ms dirty-flag timer
}
private func scheduleIfNeeded() {
    guard timerTask == nil, !isComplete else { return }
    timerTask = Task { [weak self] in
        do { try await Task.sleep(for: .milliseconds(50)) } catch { return }
        guard !Task.isCancelled else { return }
        await self?.timerFired()
    }
}
```
Fold rule — coalesce into the last block only when kinds match:
```swift
case .textDelta(let chunk):
    if case .text(let existing)? = blocks.last { blocks[blocks.count - 1] = .text(existing + chunk) }
    else { blocks.append(.text(chunk)) }
```
OpenAI reasoning summaries are *replace-on-complete*: `takeStreamingReasoningSummary()` pops the trailing `.openAIReasoning` (same model only) so `.reasoningComplete(summary:"")` keeps the streamed text but swaps in item id + encrypted content.

**Flow:** provider bytes → events → reducer mutates block list → revision++/dirty → first event publishes at once, subsequent events wait for the 50 ms timer → `complete(throwing:)` cancels the timer, force-publishes, finishes the continuation and returns the final snapshot even on error.
**Invariant:** text content is never lost by coalescing (burst test: 1,951 deltas ⇒ ≤2 published snapshots AND final text equals all 1,951 chars); `stopReason` comes only from `.messageStop`; late snapshots apply to their originating conversation, not the currently selected one.
**Probe:** `Tests/PalmierProTests/Agent/AgentStreamPresentationTests.swift:8-18` (`burstCoalescesWithoutChangingText`: `#expect(await recorder.count <= 2)` with exact text equality), `:20-47` (`reducerPreservesBlockOrderAndStopReason`: thinking→openAIReasoning→text→toolUse order preserved), `:63-89` (conversation-scoped application).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "palmier-pro", query: "AgentStreamPresentationBuffer snapshots bufferingNewest", limit: 10, fields: ["signature", "lines"] });
```

## Verdict
Adopt the actor + dirty-flag timer shape and the "coalesce into last block iff same kind" fold; adopt replace-on-complete for reasoning summaries. Adapt the 50 ms constant and snapshot payload to your UI layer. Omit the PalmierPro `AgentContentBlock` enum cases themselves. Coverage: both symbols `no_recorded_issue` @ gen 2026-08-25T19:59:55Z; tests read directly (not executed — macOS-only runner absent).
