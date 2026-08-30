<!-- capsule-v2 -->
# Steering & turn lifecycle — how does user input injected mid-run reach the model without splitting a streamed turn?

**Source:** pi-upstream MIT `main@534bcbffb7e1e7551d9ee3572dfeb278e203e493`; Codebase Memory `pi-upstream`. **Question:** A porter must let users type while the agent runs — when may queued messages enter the context?

## Drain at loop start and between turns, never mid-stream
**Path/Symbol:** `packages/agent/src/agent-loop.ts:155-275` (`runLoop` double loop), hooks consumed at `:226-259`.
**Signature:** config callbacks: `getSteeringMessages(): Promise<AgentMessage[]>` (drained pre-turn), `getFollowUpMessages(): Promise<AgentMessage[]>` (checked where the agent would stop), `prepareNextTurn(snapshot): Promise<snapshot | undefined>` (may swap context/model/thinkingLevel), `shouldStopAfterTurn(payload): Promise<boolean>`.
**Data Shape:** Outer `while(true)` = follow-up continuation after the agent would stop. Inner `while (hasMoreToolCalls || pendingMessages.length > 0)` = tool calls + steering. Pending messages are pushed to BOTH `currentContext.messages` and the run's `newMessages` before the next assistant response, each wrapped in message_start/message_end events.

### Decisive source
```ts
// Check for steering messages at start (user may have typed while waiting)
let pendingMessages: AgentMessage[] = (await config.getSteeringMessages?.()) || [];
while (true) {
	let hasMoreToolCalls = true;
	while (hasMoreToolCalls || pendingMessages.length > 0) {
		// ... inject pendingMessages BEFORE streaming ...
		const message = await streamAssistantResponse(currentContext, config, signal, emit, streamFunction);
		// ... tool batch ... turn_end ...
		const nextTurnSnapshot = await config.prepareNextTurn?.(nextTurnContext);
		if (nextTurnSnapshot) { currentContext = nextTurnSnapshot.context ?? currentContext; /* + model/thinking */ }
		if (await config.shouldStopAfterTurn?.({...})) return emit agent_end;
		pendingMessages = (await config.getSteeringMessages?.()) || [];   // re-drain AFTER every turn
	}
	const followUpMessages = (await config.getFollowUpMessages?.()) || [];
	if (followUpMessages.length > 0) { pendingMessages = followUpMessages; continue; }
	break;
}
```

**Flow:** capture is fully decoupled from application: anything typed during a streamed turn waits in a queue until the current turn ends; the drain points are loop start, after every turn, and the follow-up check at the natural stop point. Error/aborted stop reasons end the whole run immediately (`agent_end`).
**Invariant:** Steering messages NEVER interleave inside an assistant token stream — they wait for a turn boundary. Context/model swaps happen only through the post-turn snapshot, so a turn always completes with the configuration it started with.
**Probe:** `packages/agent/test/agent-loop.test.ts:681` ("should inject queued messages after all tool calls complete"), `:1031/:1104` (prepareNextTurn / shouldStopAfterTurn).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-upstream", query: "runLoop getSteeringMessages followUp", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt queue-at-boundary steering and the four-hook turn lifecycle. Adapt hook names to your config surface. Omit the outer follow-up loop if your host has no queue-while-idle feature. Coverage caveat: none.
