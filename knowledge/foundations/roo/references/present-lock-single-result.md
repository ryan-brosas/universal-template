<!-- capsule-v2 -->
# One tool_result per tool_use — how does the presentation lock prevent duplicate results, hangs, and lost rejections?

**Source:** Roo-Code Apache-2.0 `main@b867ec9145750d0ae1ff7f02d35406e9bf2a0b16`; Codebase Memory `Roo-Code`. **Question:** When streaming blocks re-trigger presentation concurrently and every native `tool_use` REQUIRES exactly one matching `tool_result`, what locking + latching discipline keeps the protocol from breaking under rejection, validation failure, or malformed args?

## Lock + pending-flag re-entrancy; latch flags; every exit pushes a result
**Path/Symbol:** `src/core/assistant-message/presentAssistantMessage.ts` (`presentAssistantMessage` :59-967; lock prologue :62-74; rejection short-circuit :388-403; missing-nativeArgs guard :407-441; one-result latch `pushToolResult`/`hasToolResult` :446-491; #10465 feedback merge :470-486 & :211-216; validation-only-when-complete :560-626; tail index advance :897-950).
**Signature:** `async function presentAssistantMessage(cline: Task): Promise<void>` (mutates Task presentation state).
**Data Shape:** Latches: `presentAssistantMessageLocked`, `presentAssistantMessageHasPendingUpdates`, `currentStreamingContentIndex`, `didRejectTool`, `didAlreadyUseTool`, `userMessageContentReady`, plus per-call `hasToolResult`.

### Decisive source
```ts
if (cline.presentAssistantMessageLocked) {
    cline.presentAssistantMessageHasPendingUpdates = true   // coalesce, don't queue
    return
}
cline.presentAssistantMessageLocked = true
// ... block = { ...assistantMessageContent[index] } SHALLOW copy on purpose:
// read-only use; protects against reference swap during streaming at ~10x less cost ...
// EVERY tool-exit path calls pushToolResult (native protocol requires a result per tool_use):
const pushToolResult = (content) => {
    if (hasToolResult) { console.warn(`Skipping duplicate tool_result ...`); return }
    // merge approval feedback INTO the result (#10465), never as a second message
}
```
Tail rule (:900+): release the lock FIRST (`presentAssistantMessageLocked = false` — recursive self-call would otherwise bounce off the pending-flag forever), then only if the block is complete/rejected/already-used: advance `currentStreamingContentIndex++`, set `userMessageContentReady` when at/past end, and recursively present the next block; finally re-run once more if pending updates were coalesced. Validation runs ONLY for `!block.partial` (validating partials would push multiple error results for one id and freeze the stream); missing-nativeArgs on a known tool pushes ONE structured is_error result without setting `didAlreadyUseTool`; after a user rejection every later block gets an auto `is_error` tool_result so the provider never sees a dangling `tool_use`.
**Flow:** trigger → lock-or-coalesce → shallow-copy block → rejection check → missing-args guard → record usage → validateToolUse (complete only) → repetition gate → dispatch to tool handler with shared askApproval/handleError closures → release lock → advance index / mark ready / recurse.
**Invariant:** At most one in-flight presentation per Task; at most ONE `tool_result` per `tool_use_id` ever reaches `userContent`; approval-with-feedback text/images ride inside that single result (#10465); a rejected stream still terminates with all tool_uses answered; partial blocks never execute, never validate.
**Probe:** `src/core/assistant-message/__tests__/presentAssistantMessage-unknown-tool.spec.ts` (:106 fail-fast missing id, :137 unknown tool "without freezing", :188 sets userMessageContentReady); `-custom-tool.spec.ts` (:87 custom_tool recording, :290 alias normalization before validateToolUse).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "Roo-Code", query: "presentAssistantMessage locked hasPendingUpdates didRejectTool pushToolResult", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the locked+pended re-entrancy pattern, the single-result latch, feedback-in-result merging, and validate-on-complete-only. Adapt Task fields to your orchestrator state. Omitting the reject-path auto-results will hard-break any provider that enforces tool_use/tool_result pairing.
