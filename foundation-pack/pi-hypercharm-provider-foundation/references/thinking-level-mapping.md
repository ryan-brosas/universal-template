<!-- capsule-v2 -->
# Thinking-level mapping: provider enums → pi levels — how do you translate a provider's reasoning surface into the host's level model?

**Source:** pi-hypercharm-provider MIT `main@4520704` (drift re-entry pass 3, was `0bdfab4`); Codebase Memory project `pi-hypercharm-provider`. **Question:** How do you convert a catalog's `reasoning_levels` / `can_reason` flags into pi's seven thinking levels, and how does a user's chosen level reach an OpenAI-compatible request body?

## buildThinkingLevelMap + ON_OFF map + transformApiModel + streamHypercharm clamp
**Path/Symbol:** `index.ts:241-264` (`PI_THINKING_LEVELS` :241, `ON_OFF_THINKING_LEVEL_MAP` :243-252, `buildThinkingLevelMap` :253-264), `index.ts:266-300` (`transformApiModel`), request-side `index.ts:585-590` (clamp+convert in `streamHypercharm`). Script twin at `scripts/update-models.js:224-236`.
**Signature:** `buildThinkingLevelMap(levels: string[]): Record<string,string|null> | undefined`; `transformApiModel(apiModel: any): JsonModel | null`.
**Data Shape:** `thinkingLevelMap?: Record<pi-level, provider-level|null>` — every pi level gets an explicit entry; `null` = unsupported.

### Decisive source
```ts
const ON_OFF_THINKING_LEVEL_MAP = {
	off: "off", minimal: null, low: null, medium: null,
	high: null, xhigh: null, max: "max",      // boolean on/off model: max selects the on state
};

function buildThinkingLevelMap(levels) {
	if (levels.length === 0) return undefined;
	const available = new Set(levels);
	const result = {
		// The provider enum uses "none" for the off state on newer deployments;
		// the official extension looked only for the older "off" spelling.
		off: available.has("off") ? "off" : available.has("none") ? "none" : null,
	};
	for (const level of PI_THINKING_LEVELS) {
		result[level] = available.has(level) ? level : null;
	}
	return result;
}
```
Request side — pi hands `options.reasoning` (raw ThinkingLevel); streamOpenAICompletions reads ONLY `reasoningEffort`:
```ts
const clampedReasoning = options?.reasoning ? clampThinkingLevel(hyperModel, options.reasoning) : undefined;
const reasoningEffort = clampedReasoning === "off" ? undefined : clampedReasoning;
const { reasoning: _reasoning, ...streamOptions } = options;
```

**Flow:** catalog model → three-way classification: has `reasoning_levels[]` ⇒ per-level identity map + `compat.supportsReasoningEffort = true`; else `can_reason === true` ⇒ boolean ON_OFF map (max ⇒ on, off ⇒ off, middle levels unsupported/null); else NO thinkingLevelMap and `reasoning:false`.
**Invariant:** the map must be TOTAL over pi's levels (`minimal…max`) with explicit nulls — partial maps make the host guess. The `"off"/"none"` dual spelling is a deployment-compat trap. `transformApiModel` returns NULL for id-less entries and the fetcher filters them out. On the wire, `off` becomes OMITTED `reasoningEffort` (undefined), not the string "off". Fixed compat defaults for this API family: `supportsStore:false`, `thinkingFormat:"deepseek"`, `maxTokensField:"max_tokens"`. ERRATUM (pass 3): the parenthetical "cacheWrite always 0 because Hyper exposes no cached-output pricing" is OBSOLETE — commit 49f661b inverted the mapping (see cache-pricing-field-remap.md); cacheWrite now carries the cached-input price.
**Probe:** no direct unit test upstream — deterministic probe: smoke suite pins the DISPLAY half of levels nowhere (out of scope), so porters re-verify against their host's clampThinkingLevel; coverage caveat recorded.
**Coverage caveat:** untested upstream; script twin keeps offline docs consistent with runtime.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-hypercharm-provider", query: "buildThinkingLevelMap", limit: 5 });
// → pi-hypercharm-provider.buildThinkingLevelMap Function index.ts 248-258
```

## Verdict
Adopt the total-map-with-nulls discipline, the off/none dual spelling, and the clamp-then-omit request conversion. Adapt level names to your host enum. Omit deepseek thinkingFormat if your endpoint differs.
