<!-- capsule-v2 -->
# Premium-pool run policy — how do you sell expensive grounded calls without them leaking into cheap plans?

**Source:** Elmo (aeo-elmo) MIT `main@da87272c`; Codebase Memory `ext-aeo-elmo`. **Question:** How are platform picks, premium slots, cadence overrides, and grounded targets resolved into one prompt's target list?

## resolvePromptRunPlan: two tiers, override only slows
**Path/Symbol:** `packages/lib/src/run-policy/policy.ts:resolvePromptRunPlan` (L67–126), `intervalForRate` (L63–65), `resolveBrandPicks` (L139–150), `defaultPlatformPicks` (L158–165); pool positions in `run-policy/maintenance.ts:computePoolPositions` (L115–142); brand-level wrapper `run-policy/brand-plans.ts` (whole, 55L).
**Signature:** `resolvePromptRunPlan(input): { targets: TargetPlan[], rescheduleHours: number | null }`; `computePoolPositions(prompts, {maxPrompts, premiumPool}): { withinPromptPool: Set, premiumByPrompt: Map }`.
**Data Shape:** standard tier = brand picks (clamped to plan menu + pick-count; null picks → plan defaults written explicitly at brand creation "so a paying org is never silently untracked") at `24/max(1,standardRunsPerDay)` hours × plan replication; premium tier = per prompt/model PAID SLOTS at premium rate × replication 1. `rescheduleHours = min(target intervals)` or null.

### Decisive source
```ts
// A pick always means the ungrounded target: the grounded one is sold from
// the premium pool below, so picking a premium model must not quietly buy
// the expensive call.
const config = input.scrapeTargets.find((t) => t.model === model && !isGroundedApiTarget(t));
…
const overrideHours = input.brand.delayOverrideHours;
const slowerOf = (planInterval: number) => Math.max(overrideHours ?? planInterval, planInterval);
```
Pool admission is oldest-first (`createdAt asc, id tiebreak`) and premium slots fill per prompt/model pair — a prompt with 2 models and 1 slot left keeps its first model ("admitting neither would strand a slot the org is paying for").

**Flow:** `resolveBrandPromptRunPlans` computes org-wide pools ONCE then resolves each requested prompt's plan against them; everything re-resolves fresh every firing so downgrades/cancellations apply without touching queued jobs.
**Invariant:** three leak-guards: (1) picks resolve to ungrounded configs only; (2) stored delay overrides can only SLOW sampling below plan rate — clamped here because a downgrade can leave a faster stored value; (3) unlimited mode reads entitlements, NOT deployment mode, because a worker whose mode flag said "not cloud" while entitlements said otherwise would run a paying customer on every platform.
**Probe:** `packages/lib/src/run-policy/policy.test.ts` + `brand-plans.test.ts` + `maintenance.test.ts` (69 tests across the three files in this probe environment).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-aeo-elmo", query: "resolvePromptRunPlan computePoolPositions resolveBrandPicks defaultPlatformPicks", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the two-tier resolution + slower-only override clamp + oldest-first pools; adapt tier names/rates to your plans; omit nothing else — each guard maps to a real billing-leak failure mode stated in-source.
