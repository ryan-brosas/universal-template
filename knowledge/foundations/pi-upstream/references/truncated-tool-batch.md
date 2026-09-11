<!-- capsule-v2 -->
# Truncated-message tool failure — what do you do with tool calls from a length-capped assistant response?

**Source:** pi-upstream MIT `main@534bcbffb7e1e7551d9ee3572dfeb278e203e493`; Codebase Memory `pi-upstream`. **Question:** A porter sees `stopReason === "length"` on an assistant message carrying tool calls — which calls may execute?

## Fail the whole batch, never execute
**Path/Symbol:** `packages/agent/src/agent-loop.ts:374-406` (`failToolCallsFromTruncatedMessage`) + dispatch at `:208-214`.
**Signature:** `failToolCallsFromTruncatedMessage(toolCalls: AgentToolCall[], emit: AgentEventSink): Promise<ExecutedToolCallBatch>` → `{ messages: ToolResultMessage[]; terminate: false }`.
**Data Shape:** Each call becomes a `toolResult` message with a text-only error result (`createErrorToolResult`), `isError: true`; full `tool_execution_start` AND `tool_execution_end` events are emitted so UIs see the lifecycle.

### Decisive source
```ts
// A "length" stop means the output was cut off by the token limit, so
// every tool call in the message may carry truncated arguments. Fail
// them all instead of executing potentially borked calls.
const executedToolBatch =
	message.stopReason === "length"
		? await failToolCallsFromTruncatedMessage(toolCalls, emit)
		: await executeToolCalls(currentContext, message, config, signal, emit);
```
And the reason per-call salvage cannot save you:
```ts
// Streamed tool-call arguments are finalized with a best-effort JSON salvage
// parser, so a truncated message can yield tool calls whose arguments parse
// and validate but are silently incomplete. None of them are safe to execute;
// report each as an error so the model can re-issue them.
```

**Flow:** stopReason "length" → EVERY tool call in that message is failed with "…may be truncated. Re-issue the tool call with complete arguments." → results enter context as normal toolResults → loop continues (the model re-issues). The batch does NOT terminate the run.
**Invariant:** A truncated message's tool calls are never trusted, even ones whose arguments parse and schema-validate — streaming salvage can produce silently incomplete but valid-looking JSON. Trust is determined by the message-level stop reason, not per-call validation.
**Probe:** `packages/agent/test/agent-loop.test.ts:371` ("should not execute tool calls from a length-truncated assistant message").

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-upstream", query: "failToolCallsFromTruncatedMessage", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt message-level distrust of tool calls under a token-limit stop; adapt the error wording to your retry convention. Omit nothing — this is the entire contract. Coverage caveat: none; directly pinned by test.
