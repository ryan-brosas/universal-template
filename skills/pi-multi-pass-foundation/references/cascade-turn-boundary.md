<!-- capsule-v2 -->
# Cascade turn boundary — how does failover survive internal replay retries without re-attempting exhausted accounts?

**Source:** pi-multi-pass MIT-declared per package.json (no LICENSE file at pin; citations-only) `main@b9d9d1d7a09252a19ec79868517d49d4f07c4760`; Codebase Memory `pi-multi-pass`. **Question:** When failover switches accounts and replays the same prompt, how does state distinguish "internal retry of the same turn" from "genuinely new user turn" so the cascade moves forward-only?

## Prompt-keyed cascade state plus a suppress flag on replay
**Path/Symbol:** `extensions/multi-sub.ts`: `FailoverCascadeState` (4349-4353), `ensureCascadeState` (2575-2597), `startTurn` (2599-2619), `clearCascadeState`/`getCascadeStateSnapshot` (2621-2634), `PoolManager.handleError` (2641-2733), event wiring `before_agent_start`/`agent_end` (5487-5534).
**Signature:** `startTurn(prompt: string | null, currentModel?: Model<Api>): void`; `ensureCascadeState(prompt: string | null, currentModel: Model<Api>): FailoverCascadeState`; `async handleError(errorMessage: string, currentModel, ctx, lastUserPrompt: string | null, config): Promise<boolean>`.
**Data Shape:** FailoverCascadeState = {prompt: string, attemptedProviders: Set<string>, visitedChainIndexes: Set<number>}; rate-limit match via RATE_LIMIT_PATTERNS = /too many requests|overloaded|capacity|429|quota|limit/i family (1932-1934).

### Decisive source
```ts
// handleError core sequence:
const cascade = this.ensureCascadeState(lastUserPrompt, currentModel);
this.markExhausted(currentModel.provider);              // BEFORE planning
const plan = this.buildFailoverPlan(currentModel, config, ctx.modelRegistry.authStorage,
	{ attemptedProviders: cascade.attemptedProviders, visitedChainIndexes: cascade.visitedChainIndexes });
await this.reorderCandidatesByStrategy(pool, plan, currentModel, ctx, cascade, lastUserPrompt);
// ... switch to plan.candidates[0] via setModel; on success:
cascade.attemptedProviders.add(nextCandidate.provider);
if (typeof nextCandidate.chainIndex === "number") cascade.visitedChainIndexes.add(nextCandidate.chainIndex);
if (lastUserPrompt) {
	this.suppressNextStartTurn = true;
	this.pi.sendUserMessage(lastUserMessage);            // replay same prompt
}
// startTurn consumes the flag FIRST, keeping cascade state alive:
startTurn(prompt, currentModel) {
	if (this.suppressNextStartTurn) { this.suppressNextStartTurn = false; return; }
	if (!prompt) { this.cascadeState = null; return; }
	if (!this.cascadeState || this.cascadeState.prompt !== prompt) { /* fresh state */ return; }
	if (currentModel) this.cascadeState.attemptedProviders.add(currentModel.provider);
}
```

**Flow:** new user prompt -> startTurn stores prompt-keyed state seeded with the starting provider -> assistant turn ends with stopReason "error" + rate-limit message -> handleError: ensure state (same prompt reuses and adds current provider), mark current exhausted BEFORE planning (planner then cannot pick it), build plan honoring attemptedProviders/visitedChainIndexes, reorder, notify each skip with the continuation phrase, switch on first candidate (model-missing or auth-unavailable at switch => announce exhaustion, return false) -> after a SUCCESSFUL switch record attempted provider (+ visited chain index for chain-sourced candidates) -> replay the stored prompt with suppressNextStartTurn=true so the replayed turn does NOT reset the cascade -> next handleError continues forward-only; when nobody is eligible, multiSub reports "All members rate limited. Try again in a few minutes."
**Invariant:** mark-before-plan prevents self-selection; attempt-recording happens only AFTER a confirmed switch, so a failed switch does not poison the set; the cascade lives exactly as long as the prompt text stays identical — a genuinely new prompt resets it, an empty prompt clears it; rotation returns true only when a real switch happened, letting callers distinguish rotated vs exhausted.
**Probe:** `node tests/runtime-failover-check.mjs --retry-start-turn --no-loop` (retry-start-turn pins two consecutive 429s advancing anthropic -> anthropic-2 -> anthropic-3 with NO already-attempted false skips and setModelCalls exactly ["anthropic-2:...","anthropic-3:..."], runtime-failover-check.mjs:684-717; green at b9d9d1d7a092).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-multi-pass", query: "ensureCascadeState startTurn suppressNextStartTurn handleError", limit: 10, fields: ["signature"] });
```

## Verdict
Adopt the three-part protocol: prompt-keyed cascade state, mark-exhausted-before-plan, record-after-switch, and the suppress-next-turn-start replay guard. Adapt sendUserMessage/setModel to your host's turn and model-switch APIs; classify errors with your own pattern table. Omit the pi ExtensionAPI event names; map agent_end/before_agent_start onto your runtime's equivalents.
