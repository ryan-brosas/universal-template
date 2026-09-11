<!-- capsule-v2 -->
# Repetition circuit breaker — how do you stop a stuck tool loop while keeping human guidance as the recovery path?

**Source:** Roo-Code Apache-2.0 `main@b867ec9145750d0ae1ff7f02d35406e9bf2a0b16`; Codebase Memory `Roo-Code`. **Question:** A porter's agent repeats the same failing call forever — when to block, and what unblocks it?

## Canonical-JSON identity, block at limit, RESET on block
**Path/Symbol:** `src/core/tools/ToolRepetitionDetector.ts:1-89` (whole file).
**Signature:** `check(currentToolCallBlock: ToolUse): { allowExecution: boolean; askUser?: { messageKey, messageDetail } }`; `constructor(limit = 3)`.
**Data Shape:** Serialization = safe-stable-stringify (sorted keys) over `{name, params}` plus `nativeArgs` ONLY when non-empty — stable across parser variants; limit ≤ 0 means unlimited.

### Decisive source
```ts
if (this.consecutiveIdenticalToolCallLimit > 0 &&
	this.consecutiveIdenticalToolCallCount >= this.consecutiveIdenticalToolCallLimit) {
	// Reset counters to allow recovery if user guides the AI past this point
	this.consecutiveIdenticalToolCallCount = 0
	this.previousToolCallJson = null
	return { allowExecution: false,
		askUser: { messageKey: "mistake_limit_reached", messageDetail: t("tools:toolRepetitionLimitReached", ...) } };
}
```

**Flow:** each tool call → canonical JSON → identical-to-previous increments the counter, ANY different call resets it → at the limit, block + ask the user AND reset internal state so the user's guidance re-enables the tool instead of leaving a permanent ban. Pairs with Task-level consecutiveMistakeLimit (same default 3): per-tool-shape repetition here, per-turn-quality mistakes there.
**Invariant:** A repetition guard must distinguish "stuck" from "banned" — blocking is temporary and self-clearing through human intervention; identity comparison must be canonicalization-based (sorted keys), not reference equality.
**Probe:** `src/core/tools/__tests__/ToolRepetitionDetector.spec.ts` (:128 blocks at limit, :149 "should reset internal state after limit is reached", :88 reset-on-different-call).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "Roo-Code", query: "ToolRepetitionDetector serializeToolUse consecutive", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt canonical-JSON consecutive-identity detection with reset-on-block. Adapt the limit and i18n keys. Omit nativeArgs handling if your parser has no dual representation. Coverage caveat: none — directly spec-pinned.
