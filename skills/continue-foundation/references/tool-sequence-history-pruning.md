<!-- capsule-v2 -->
# Tool-sequence-preserving history pruning — how does compileChatMessages cut old messages without ever orphaning a tool response?

**Source:** Continue (Apache-2.0) `main@5522c6f44ca0ac3528b37244818fbfa39b5af470`; Codebase Memory `continue`. **Question:** When history exceeds the context window, which messages are non-negotiable, and how is the tail tool sequence kept intact while older messages are shifted away?

## Non-negotiables first, then shift-from-front
**Path/Symbol:** `core/llm/countTokens.ts:compileChatMessages` (:422-551) + `extractToolSequence` (:228-280).
**Signature:** `compileChatMessages({modelName, msgs, knownContextLength, maxTokens, supportsImages, tools}): CompiledMessagesResult` where result = `{compiledChatMessages, didPrune, contextPercentage}`.
**Data Shape:** in → ChatMessage[]; out → pruned array + flag + utilization ratio. Budget: `contextLength − safetyBuffer(min(1000, 2% of context)) − min(1000, maxTokens)`.

### Decisive source
```ts
// extractToolSequence: [assistant_with_tool_calls, tool_1, ..., tool_n] OR a single user message
if (lastMsg.role === "tool") {
  toolSequence.push(lastMsg);
  while (messages.length > 0 && messages[messages.length - 1].role === "tool")
    toolSequence.unshift(messages.pop()!);
  const assistantMsg = messages.pop();
  if (assistantMsg) {
    toolSequence.unshift(assistantMsg);
    for (const toolMsg of toolSequence.slice(1))
      if (toolMsg.role === "tool" && !messageHasToolCallId(assistantMsg, toolMsg.toolCallId))
        throw new Error(`...no tool call found to match tool output for id "${toolMsg.toolCallId}"`);
  }
}
```
```ts
// budget ladder — throw BEFORE pruning when non-negotiables alone exceed context
inputTokensAvailable -= countingSafetyBuffer;
inputTokensAvailable -= minOutputTokens;   // Math.min(MIN_RESPONSE_TOKENS=1000, maxTokens)
inputTokensAvailable -= toolTokens; inputTokensAvailable -= systemMsgTokens; inputTokensAvailable -= lastMessagesTokens;
if (knownContextLength !== undefined && inputTokensAvailable < 0) { throw new Error(...) }
// prune loop with orphan guard
while (historyWithTokens.length > 0 && currentTotal > inputTokensAvailable) {
  const message = historyWithTokens.shift()!;
  currentTotal -= message.tokens; didPrune = true;
  while (historyWithTokens[0]?.role === "tool") { currentTotal -= historyWithTokens.shift()!.tokens; }
}
// reassemble: [system, ...prunedHistory, ...toolSequence]
```

**Flow:** flatten image parts if `supportsImages === false` → lift out system message → drop empty messages (`addSpaceToAnyEmptyMessages` re-fills blanks so framing stays valid) → `extractToolSequence` pops the tail (validating every tool output against an assistant `toolCalls` id, THROWING on orphans) → reserve system/tools/tail tokens FIRST (loud throw if they don't fit) → shift oldest messages until under budget, dragging trailing tool responses along so no call loses its outputs → reassemble `[system, history, toolSequence]`.
**Invariant:** The LAST user-or-tool sequence is never pruned; the system message and tools are never pruned; a tool response can never end up separated from its assistant tool-call (the inner `while role==="tool"` drain runs after EVERY removal). Pruning only happens when `knownContextLength` is known — unknown context length skips the throw AND the loop. `contextPercentage` is measured against `contextLength − buffer − minOutput`, not the raw window.
**Probe:** `core/llm/countTokens.test.ts:51/:57/:63/:75/:83` pin the line-pruning twins (`pruneLinesFromTop/Bottom`); deterministic source pin for the sequence validator: `grep -n 'no tool call found to match' core/llm/countTokens.ts`. Coverage caveat recorded: no dedicated vitest suite for `compileChatMessages` itself at this pin — behavior pinned by decisive source ranges.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "continue", query: "compileChatMessages extractToolSequence prune", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt non-negotiable-first budgeting, loud throw before silent truncation, and the orphan-guarded front-shift; adapt the constants (1000-token floors, 2% buffer) to your product; omit image flattening only if your host guarantees image-capable models.
