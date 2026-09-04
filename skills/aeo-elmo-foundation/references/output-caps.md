<!-- capsule-v2 -->
# Output-cap honesty — what do you do when a tracked answer was clipped?

**Source:** Elmo (aeo-elmo) MIT `main@da87272c`; Codebase Memory `ext-aeo-elmo`. **Question:** How are max-token limits set per provider, and how is a truncated answer handled so it doesn't silently skew metrics?

## Store anyway, warn loudly
**Path/Symbol:** `packages/lib/src/providers/config.ts:API_PROVIDER_MAX_OUTPUT_TOKENS` (L13–18), `warnIfOutputCapped` (L26–32), search budgets (L34–47).
**Signature:** `warnIfOutputCapped(provider: string, model: string, finishReason: unknown): void`; constants `ANTHROPIC_WEB_SEARCH_MAX_USES = 1`, `OPENAI_WEB_SEARCH_MAX_TOOL_CALLS = 2`, `OPENAI_WEB_SEARCH_CONTEXT_SIZE = "low"`, `RESEARCH_WEB_SEARCH_MAX_USES = 5`, `RESEARCH_WEB_SEARCH_CONTEXT_SIZE = "medium"`.
**Data Shape:** 8000-token caps for all four direct-API providers — "a worst-case bound on a single tracked run, not a target length — sized well above any answer we expect, so hitting one means something went wrong". Caps cover reasoning/thinking tokens too.

### Decisive source
```ts
// A capped response still stores as a normal run, so a clipped answer would
// land as a real-looking result with fewer brand mentions rather than an error.
// Log it — deliberately without failing the run — so the caps above can be
// tuned from evidence.
if (finishReason === "length" || finishReason === "max_tokens") console.warn(`[${provider}] hit the output cap …`);
```

**Flow:** recurring tracked runs get tight budgets (they are the cost surface); the one-shot onboarding research path gets a deeper budget (5 searches / medium context) because it does not recur. Anthropic bills native web search PER USE, hence max_uses=1.
**Invariant:** never fail or discard a capped run (it still costs money and still happened), but never let clipping be invisible either — the warning exists to tune caps from evidence. The two-tier budget split (recurring vs one-shot) must stay asymmetric on purpose.
**Probe:** `packages/lib/src/providers/config.test.ts` (GREEN in probe run).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-aeo-elmo", query: "warnIfOutputCapped API_PROVIDER_MAX_OUTPUT_TOKENS RESEARCH_WEB_SEARCH_MAX_USES", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt store-and-warn + two-tier budgets; adapt token numbers to your models; omit nothing else — the comment chain encodes the cost reasoning you'd otherwise re-derive wrongly.
