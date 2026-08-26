<!-- capsule-v2 -->
# Worker-loop budget — one bounded AgentLoopConfig shape, repeated identically across all three workers

**Source:** pi-observational-memory MIT `master@ce9fc982b3a219a7839f07c9f4a3e054e81a2b21`; Codebase Memory `pi-observational-memory`. **Question:** How do you run a small tool-collecting LLM worker loop against an arbitrary host model without overflowing it, sending unsupported thinking options, or letting an unbounded run spin?

## Path/Symbol
**Path:** `src/model-budget.ts` :3-9; identical config assembly in `src/agents/observer/agent.ts` :189-213, `src/agents/reflector/agent.ts` :172-194, `src/agents/dropper/agent.ts` :239-256; thinkingLevel threading from `src/hooks/consolidation-trigger.ts` :320 (observer), :391 (reflector), :465 (dropper).

**Signature:** `boundedMaxTokens(model: Model<any>, requested: number = AGENT_LOOP_MAX_TOKENS): number` with `AGENT_LOOP_MAX_TOKENS = 32_000`.

**Data Shape:** every worker's `AgentLoopConfig` carries: `{ model, apiKey, headers, env, maxTokens: boundedMaxTokens(model), convertToLlm, toolExecution: "sequential", ...(reasoning && thinkingLevel !== "off" ? { reasoning } : {}), ...(maxTurns > 0 ? { shouldStopAfterTurn } : {}) }`.

### Decisive source
```ts
// model-budget.ts — the whole module
export const AGENT_LOOP_MAX_TOKENS = 32_000;
export function boundedMaxTokens(model: Model<any>, requested: number = AGENT_LOOP_MAX_TOKENS): number {
	return typeof model.maxTokens === "number" && model.maxTokens > 0
		? Math.min(model.maxTokens, requested)
		: requested;
}
```
```ts
// agents/*/agent.ts — identical in all three workers
const reasoning = (model as { reasoning?: unknown }).reasoning;
const thinkingLevel = args.thinkingLevel ?? "low";
const effectiveMaxTurns = args.maxTurns && args.maxTurns > 0 ? args.maxTurns : undefined;
let turnCount = 0;
const config: AgentLoopConfig = {
	model, apiKey, headers, env,
	maxTokens: boundedMaxTokens(model, AGENT_LOOP_MAX_TOKENS),
	convertToLlm: (msgs) => msgs as Message[],
	toolExecution: "sequential",
	...(reasoning && thinkingLevel !== "off" ? { reasoning: thinkingLevel } : {}),
	...(effectiveMaxTurns !== undefined ? { shouldStopAfterTurn: () => ++turnCount >= effectiveMaxTurns } : {}),
};
```

**Flow:** caller passes `thinkingLevel: runtime.config.model?.thinking ?? "low"` and `maxTurns: runtime.config.agentMaxTurns` → worker clamps its loop budget to the model's own advertised maxTokens (32k default when the model reports none or a non-positive value) → thinking option spreads ONLY when the model advertises a `.reasoning` capability AND the level isn't "off" → maxTurns gates via a closure counter checked after each turn → tools execute sequentially while tool-closure callbacks accumulate validated records.

**Invariant:** The repetition IS the pattern: three files carry byte-equivalent config assembly, so porters should extract ONE helper rather than diverge per stage. Capability-gating prevents shipping `reasoning` params to models that lack them (host session models are arbitrary); `thinkingLevel ?? "low"` gives cheap-but-not-zero deliberation for background work; `maxTurns <= 0`/undefined means UNLIMITED turns (the gate is opt-in); unknown model budgets keep the 32k default instead of failing. The drain loops stay dumb — they only watch for terminal stopReason errors (stream-errors) while tool closures collect.

**Probe (direct tests):**
```bash
cd /mnt/hdd/utopia/inspo/pi-observational-memory && \
grep -c "boundedMaxTokens(model, AGENT_LOOP_MAX_TOKENS)" src/agents/observer/agent.ts src/agents/reflector/agent.ts src/agents/dropper/agent.ts   # 1 / 1 / 1 && \
npx vitest run tests/observer.test.ts tests/reflector.test.ts tests/dropper.test.ts   # all pass;
# suites drive the real agentLoop fake so maxTurns/thinking threading is exercised end-to-end
# (e.g. reflector pin asserts maxTurns + thinkingLevel:"minimal" forwarding through the trigger)
```

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-observational-memory", query: "boundedMaxTokens AGENT_LOOP_MAX_TOKENS shouldStopAfterTurn thinkingLevel", limit: 10 });
// rank1 resolves pi-observational-memory.src.model-budget.boundedMaxTokens Function src/model-budget.ts 5-9
```

**Verdict:** Adopt the single bounded-config shape: min(advertised, 32k default) loop budget, capability-gated reasoning spread, opt-in turn cap via counter closure, sequential tool execution. Adapt defaults to your host's economics. Omit nothing behavioral — the clamp's else-branch (keep requested on unknown caps) is what keeps arbitrary host models working.
