<!-- capsule-v2 -->
# Agent loop modes — how do you start vs resume an agent run without corrupting message history?

**Source:** pi-upstream MIT `main@534bcbffb7e1e7551d9ee3572dfeb278e203e493`; Codebase Memory `pi-upstream`. **Question:** A porter must add a "retry" entry point to their agent loop — what may it validate, and why can't it validate more?

## Two entries, one shared runLoop
**Path/Symbol:** `packages/agent/src/agent-loop.ts:31-93` (`agentLoop`, `agentLoopContinue`) and `:95-143` (`runAgentLoop`, `runAgentLoopContinue`).
**Signature:** `agentLoop(prompts: AgentMessage[], context: AgentContext, config: AgentLoopConfig, signal: AbortSignal | undefined, streamFn: StreamFn): EventStream<AgentEvent, AgentMessage[]>` · `agentLoopContinue(context, config, signal, streamFn)` (no prompts).
**Data Shape:** Both return an `EventStream<AgentEvent, AgentMessage[]>` that ends on the `agent_end` event carrying all new messages. `runAgentLoop` copies prompts into both `newMessages` and `currentContext.messages`; continue mode starts with `newMessages = []`.

### Decisive source
```ts
export function agentLoopContinue(context, config, signal, streamFn) {
	if (context.messages.length === 0) {
		throw new Error("Cannot continue: no messages in context");
	}
	if (context.messages[context.messages.length - 1].role === "assistant") {
		throw new Error("Cannot continue from message role: assistant");
	}
	// docstring: "The last message in context must convert to a `user` or `toolResult`
	// via convertToLlm. ... This cannot be validated here since convertToLlm is only
	// called once per turn."
```

**Flow:** start mode → append prompts → emit agent_start/turn_start + message events for prompts → shared `runLoop`. Continue mode → cheap preconditions only → same `runLoop` with empty `newMessages`. The LLM-boundary conversion (`config.convertToLlm`) happens exactly once per turn inside `streamAssistantResponse`, so deeper validity of the trailing message is unknowable at the loop entry.
**Invariant:** The harness carries `AgentMessage` everywhere; conversion to provider `Message[]` occurs ONLY at the LLM boundary, once per turn. Entry guards may therefore check only cheap invariants (non-empty context, last role ≠ assistant) — anything else would duplicate or contradict boundary logic.
**Probe:** `packages/agent/test/agent-loop.test.ts:1486` ("should throw when context has no messages") and `:1505/:1547` (continue without user-message events; custom-type last message allowed as caller responsibility).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-upstream", query: "agentLoopContinue precondition", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the two-mode split (start appends prompts; retry resumes without adding) and the cheap-guard-with-documented-reason pattern. Adapt guard messages to your error taxonomy. Omit pi's EventStream wrapper if your host already has an async event channel. Coverage caveat: none for this seam — direct tests pin both throws.
