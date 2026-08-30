<!-- capsule-v2 -->
# Usage attribution ledger — how do you bill-grade count paid attempts?

**Source:** Elmo (aeo-elmo) MIT `main@da87272c`; Codebase Memory `ext-aeo-elmo`. **Question:** What gets recorded per provider call, and why does the runaway ceiling count events rather than runs?

## One row per attempt, success or failure, never throws
**Path/Symbol:** `apps/worker/src/jobs/process-prompt.ts:recordUsageEvent` (L302–325), `isOrgOverDailyCeiling` (L193–201); estimates `packages/lib/src/usage/cost.ts:estimateRunCostUsd` (L33–41); ceiling `run-policy/policy.ts:dailyRunCeiling` (L248–257).
**Signature:** `recordUsageEvent({organizationId, brandId, promptId, eventType: "prompt_run"|"prompt_run_failed", config}): Promise<void>`; `estimateRunCostUsd(provider, webSearchEnabled): number | null`.
**Data Shape:** usage_events row = org/brand/prompt + event type + provider/model/webSearch + units:1 + `estimatedCostUsd` at 6-decimal string (`cost === null ? null : cost.toFixed(6)`). Unknown provider → null cost, row still written.

### Decisive source
```ts
// Counts usage_events rather than prompt_runs because a retry storm writes no
// prompt_runs rows but burns spend — counting attempts is the stronger meaning
// for a safety ceiling. usage_events also has the org_id denormalized and an
// index on (organization_id, created_at), so this scan is cheap.
const [row] = await db.select({ value: sql<number>`COUNT(*)` }).from(usageEvents)
	.where(and(eq(usageEvents.organizationId, organizationId), gt(usageEvents.createdAt, sql`now() - interval '24 hours'`)));
```
Ceiling is plan-derived, not usage-derived: `Math.ceil(1.5 × (maxPrompts × platformPicks × standardRunsPerDay × replication + premiumPool × premiumRunsPerDay))`, null when unlimited.

**Flow:** run success → `prompt_run` after saveCitations; run failure → `prompt_run_failed` inside the catch before rethrow; recordUsageEvent wraps everything in try/catch and only logs — "attribution must not break tracking". The worker checks the ceiling before spending and skips the cycle (with a fingerprinted Sentry warning) when over.
**Invariant:** failed attempts MUST be counted (they cost money too) — this is exactly what makes the ceiling a spend guard instead of a success counter.
**Probe:** `packages/lib/src/usage/cost.test.ts` (per-provider estimates, anthropic web-search surcharge, null-provider → null).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-aeo-elmo", query: "recordUsageEvent isOrgOverDailyCeiling dailyRunCeiling estimateRunCostUsd", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the always-write-both-outcomes ledger and plan-derived ceiling; adapt estimate constants (deliberately coarse, in-source warning to move them to env if they ever approach list prices); omit the projection helper if you have no self-host cost page.
