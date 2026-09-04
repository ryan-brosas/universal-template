<!-- capsule-v2 -->
# Tool dispatch contract — how does every tool_use get exactly one tool_result even when a branch fails or is unknown?

**Source:** mike AGPL-3.0 `main@3ad9a5ff`; Codebase Memory `ext-mike`. **Question:** What does the dispatcher owe the model after a batch of tool calls, and what must it never do mid-batch?

## Sequential dispatch + call-id-keyed result join + synthesized fallback
**Path/Symbol:** `backend/src/lib/chat/tools/toolDispatcher.ts:257` (`runToolCalls`), `:346` (`registerGeneratedDocument`), `:90` (`normalizeAskInputsEvent`); result-join at `streaming.ts:569-591`. Direct tests: `src/lib/__tests__/documentContext.test.ts` (dispatcher-level, 16 cases) + `src/lib/chat/tools/courtlistenerTurnState.test.ts`.
**Signature:** `runToolCalls(toolCalls, docStore, userId, db, write, …) -> {toolResults, docsRead, docsFound, docsCreated, docsReplicated, workflowsApplied, docsEdited, askInputsEvents, courtlistenerEvents, caseCitationEvents, mcpEvents}`.
**Data Shape:** eleven typed result buckets; SSE events written inline per branch; `ask_inputs` produces NO tool result — instead it pauses the whole turn.

### Decisive source
```ts
// Index alignment would break if any tool branch skips its push (unhandled
// tool name, disabled store, guard failure). Each tool_result already carries
// its tool_call_id, so key off that directly — and fall back with an error
// result for ANY tool_use that didn't produce one, so Claude's next request
// has a tool_result for EVERY tool_use it sent.
const resultByCallId = new Map(toolResults.map(r => [r.tool_call_id, String(r.content ?? "")]));
return toolCalls.map(c => ({ tool_use_id: c.id,
    content: resultByCallId.get(c.id) ?? JSON.stringify({ error: `Tool '${c.function.name}' is not available.` }) }));
```

**Flow:** args parsed per-call with silent `{}` fallback on malformed JSON → mcp_-prefixed names route to connectors → known tools handled in an else-if chain writing lifecycle events (doc_read_start→doc_read etc.) → ask_inputs events collected then thrown as AssistantStreamAskInputsPause AFTER the batch (model never sees its own picker as a tool result).
**Invariant:** Never throw out of the loop for per-tool failures — emit UI-shaped failure events + error-content results (see edit_document's start→done-with-error pairing). Unknown tool names are caught by the join-layer synthesis, never silently dropped. Duplicate reads short-circuit via turnReadState BEFORE re-fetching bytes.
**Probe:** `grep -c "is not available" src/lib/chat/streaming.ts` → 1; `grep -c 'it(' src/lib/__tests__/documentContext.test.ts | head -1` → 17.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-mike", query: "runToolCalls replicate_document tool dispatcher", limit: 10 });
```

## Verdict
Adopt sequential dispatch + id-keyed result join + synthesized not-available fallback + pause-not-result for user-input tools; adapt bucket/event vocabulary to your client.
