<!-- capsule-v2 -->
# Agent loop semantics — how does a core loop interleave streamed responses, tool batches, steering injections, and termination without losing truncated-output safety?

**Source:** pi-mono MIT `main@80e62761f7251a104f1b21d9c73920c720f0ec00`; Codebase Memory `pi-mono`. **Question:** what are the exact continue/stop rules of a two-tier agent loop with user-steering hooks?

## Two-tier loop with steering/follow-up hooks
**Path/Symbol:** `packages/agent/src/agent-loop.ts:runLoop` (155-275); entry wrappers `agentLoop` (31-54, returns EventStream immediately), `agentLoopContinue` (64-93, validates last message is not assistant); `streamAssistantResponse` (281-372); `failToolCallsFromTruncatedMessage` (381-406).
**Signature:** internal `runLoop(initialContext, newMessages, initialConfig, signal, emit, streamFunction): Promise<void>`; public `agentLoop(prompts, context, config, signal, streamFn): EventStream<AgentEvent, AgentMessage[]>`.
**Data Shape:** config hooks: `getSteeringMessages()`, `getFollowUpMessages()`, `prepareNextTurn(ctx)` returning `{context?, model?, thinkingLevel?}`, `shouldStopAfterTurn(ctx)`; batch result `{messages: ToolResultMessage[], terminate: boolean}`.

### Decisive source
```ts
let pendingMessages = (await config.getSteeringMessages?.()) || [];
while (true) {                       // OUTER: follow-ups keep it alive
	let hasMoreToolCalls = true;
	while (hasMoreToolCalls || pendingMessages.length > 0) {   // INNER
		if (pendingMessages.length > 0) { /* emit + append steering msgs */ pendingMessages = []; }
		const message = await streamAssistantResponse(currentContext, config, signal, emit, streamFunction);
		if (message.stopReason === "error" || message.stopReason === "aborted") {
			await emit({ type: "turn_end", message, toolResults: [] });
			await emit({ type: "agent_end", messages: newMessages }); return;
		}
		const toolCalls = message.content.filter((c) => c.type === "toolCall");
		hasMoreToolCalls = false;
		if (toolCalls.length > 0) {
			const executedToolBatch = message.stopReason === "length"
				? await failToolCallsFromTruncatedMessage(toolCalls, emit)
				: await executeToolCalls(currentContext, message, config, signal, emit);
			hasMoreToolCalls = !executedToolBatch.terminate;
		}
		await emit({ type: "turn_end", message, toolResults });
		/* prepareNextTurn may swap context/model/thinkingLevel for the NEXT turn */
		if (await config.shouldStopAfterTurn?.({...})) { await emit({type:"agent_end"}); return; }
		pendingMessages = (await config.getSteeringMessages?.()) || [];
	}
	const followUpMessages = (await config.getFollowUpMessages?.()) || [];
	if (followUpMessages.length > 0) { pendingMessages = followUpMessages; continue; }
	break;
}
await emit({ type: "agent_end", messages: newMessages });
```

**Flow:** inner turn: inject queued steering messages BEFORE the next response → stream assistant response (partials pushed into `context.messages`, replaced by final on done/error) → error|aborted ends everything after turn_end+agent_end → tool calls execute (or all fail on truncation) → turn_end → prepareNextTurn snapshot swap → shouldStopAfterTurn early exit → poll steering. When inner loop drains, outer polls follow-up messages: any found restart the inner loop, else final agent_end.
**Invariant:** `stopReason === "length"` means output hit the token limit, so EVERY tool call in that assistant message fails with an error result and `terminate: false` — streamed arguments can parse yet be silently incomplete, so none are safe to execute; the model must re-issue complete arguments. Steering messages never split a tool batch. `agent_end` fires exactly once per run on every exit path (error, aborted, shouldStopAfterTurn, natural end).
**Probe:** `packages/agent/test/agent-loop.test.ts` — EXECUTED 2026-08-25 within the passing 3-file / 47-test vitest run (covers loop hooks incl. test-local prepareNextTurn/getSteeringMessages/getFollowUpMessages/shouldStopAfterTurn fixtures).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-mono", name_pattern: "(agentLoop|runAgentLoop)", file_pattern: "packages/agent/src" });
```

## Verdict
Adopt the two-tier structure, hook seam names, event ordering, and especially the length-truncation fail-all rule. Adapt hook signatures to your host context object. Omit pi’s AgentMessage/convertToLlm boundary unless you also port its message model; keep the invariant that conversion happens once per turn at the LLM call site.
