<!-- capsule-v2 -->
# Agent run loop — how does a turn loop survive cancellation, refusal, and half-finished tool calls without corrupting the conversation?

**Source:** PalmierPro GPL-3.0 `main@49841f35b3eafa65c7eadc7b168bcc74db632906`; Codebase Memory `palmier-pro`. **Question:** What is the exact termination/repair algebra of a tool-use agent loop so a porter never appends an assistant tool_use without its tool_result?

## Bounded runLoop + orphan repair
**Path/Symbol:** `Sources/PalmierPro/Agent/Chat/AgentService.swift:runLoop` (413–494), `runPendingToolUses` (557–586), `resolveOrphanToolUses` (603–640).
**Signature:** `private func runLoop(conversationID: UUID, traceID: UUID, settings: AgentRunSettings) async`; `private func resolveOrphanToolUses(reason: String = "Cancelled")`.
**Data Shape:** in-app `messages: [AgentMessage]` (role .user/.assistant/.system, blocks incl. `.toolUse(id, name, inputJSON)` / `.toolResult(toolUseId, content, isError)`); exits set `streamError` (.unavailable/.upstream/.refusal) or break on `.endTurn`.

### Decisive source
```swift
loop: while !Task.isCancelled {
    resolveOrphanToolUses()
    ...
    let stopReason = finalSnapshot.stopReason
    dropEmptyAssistantTurn(id: assistantID, conversationID: conversationID)
    if stopReason == .refusal { streamError = .refusal(chosenModel); break loop }
    if stopReason == .toolUse {
        await runPendingToolUses(assistantID: assistantID, conversationID: conversationID)
        if Task.isCancelled { break loop }
        continue loop
    }
    break loop
}
```
And the repair rule — every unresolved tool id gets a synthetic error result, inserted into the next message if it already is a tool-result user message, else as a new user message:
```swift
let synthetic: [AgentContentBlock] = orphans.map {
    .toolResult(toolUseId: $0, content: [.text(reason)], isError: true)
}
if nextIsToolResult { messages[next].blocks.insert(contentsOf: synthetic, at: 0) }
else { messages.insert(AgentMessage(role: .user, blocks: synthetic), at: next) }
```

**Flow:** client select → skill sync/reload → per iteration: orphan repair → snapshot API messages → append empty assistant → stream via `client.stream(system: instructions+skillsSection, tools, messages, context)` → present snapshots → drop empty assistant turn → branch on stop reason (.refusal ends; .toolUse runs pending tool uses and continues; otherwise ends). Every catch path also drops the empty assistant turn before recording `streamError`.
**Invariant:** no assistant `.toolUse` block may lack a matching `.toolResult` in a later user block when the next provider turn is built; cancelled or failed tool executions still emit `.toolResult(isError: true)` (`runPendingToolUses` appends `"Cancelled"` error results for uses skipped mid-flight).
**Probe:** `Tests/PalmierProTests/Agent/AgentStreamPresentationTests.swift` pins snapshot→conversation application (`lateSnapshotUpdatesOriginatingSessionAfterSwitch`: late snapshots land in the originating session, not the selected one); orphan repair itself is exercised at every loop entry — direct unit test absent, verified from source only.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "palmier-pro", query: "resolveOrphanToolUses runPendingToolUses", limit: 10, fields: ["signature", "lines"] });
```

## Verdict
Adopt the loop skeleton: orphan repair *before each iteration*, stop-reason algebra (.endTurn/.toolUse/.refusal), empty-assistant-turn cleanup on all exits, and per-tool cancel-to-error-result coercion. Adapt `SkillStore.shared.waitForSkillSync()` ordering and the `AgentRequestContext` span fields to your host. Omit the Convex-backed client selection (`selectClient`) and hosted-proxy specifics. Coverage caveat: all three symbols `no_recorded_issue` @ gen 2026-08-25T19:59:55Z; no dedicated upstream test for `resolveOrphanToolUses` — source-pinned.
