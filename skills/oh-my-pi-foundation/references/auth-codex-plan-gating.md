<!-- capsule-v2 -->
# Codex plan gating & model-policy scopes — how does model-aware routing respect free/paid/pro account tiers without locking out grandfathered accounts?

**Source:** oh-my-pi (see pack SKILL.md Provenance) MIT; Codebase Memory `oh-my-pi`. **Question:** How is a plan requirement derived from a model id, when is it enforced, and how do entitlement blocks stay scoped to one model?

## Codex plan gating & model-policy scopes
**Path/Symbol:** `packages/ai/src/auth-storage.ts:` `resolveOpenAICodexPlanRequirement` (1021–1028) + plan token tables (:993–1012) + `classifyOpenAICodexPlan` (1064–1074) + `getOpenAICodexPlanPriority` (1086–1089) + `modelAccountPolicyBlockScope` (1032–1038) + enforcement ladder in `#resolveOAuthSelection` (5010–5044).
**Signature:** requirement = `none | paid | pro`; eligibility tri-state `true | false | undefined` (unknown); scope = `` `model-policy:<bareModelId>` ``.
**Data Shape:** Plan class parsed from `UsageReport.metadata.planType` (normalized, `chatgpt_` prefix stripped, `_`-tokenized): `pro_lite→paid`, tokens {pro}→pro, {plus,business,team,enterprise,edu,...}→paid, {free,go}→free.

### Decisive source
```ts
if (bareModelId.includes("-spark")) return "pro";
if (bareModelId === "gpt-5.6" || GPT_56_PAID_CODEX_MODEL_PATTERN.test(bareModelId)) return "paid";
...
// Enforce a tier only when at least one account is CONFIRMED eligible. If every
// report is unknown or ineligible, preserve trial/grandfathered access by
// allowing the normal candidate fallback to attempt the request.
const enforcePlanRequirement =
	hasPlanRequirement &&
	candidates.some(candidate => getOpenAICodexPlanEligibility(candidate.usage, planRequirement) === true);

// Plan-gated Codex models rank on every resolve to re-verify account tiers,
// so the drain-urgency order can flip between two eligible accounts as their
// usage headroom shifts.
const passes: Array<{ allowBlocked: boolean; enforcePlanRequirement: boolean }> = [
	{ allowBlocked: false, enforcePlanRequirement },
	{ allowBlocked: true, enforcePlanRequirement },
];
if (enforcePlanRequirement) passes.push({ allowBlocked: true, enforcePlanRequirement: false });
```

**Flow:** resolve derives the requirement from provider+modelId; ranking adds `planPriority` 0/1/2 (eligible < unknown < ineligible) ahead of the boost check; then up to THREE passes run: unblocked+plan-filtered → blocked-allowed+plan-filtered (earliest-unblocking first) → blocked-allowed UNFILTERED ("the server is the final arbiter of model access"). A pinned session credential is promoted back to the front while unblocked and still plan-eligible so an active session never silently migrates accounts mid-conversation (:5017–5038). Exact Codex entitlement denials block ONLY `model-policy:<model>` scope via `rotateSessionCredential` (:6436–6461), with strict identity checks (`isCodexChatGPTAccountPolicyError(error, provider, modelId)`) because the denial sentence is provider-controlled input.
**Invariant:** Unknown plan never equals ineligible — eligibility must be POSITIVE evidence. The third pass exists so plan metadata gaps degrade to server-authoritative behavior instead of hard-failing paid-gated models on trial accounts.
**Probe:** `packages/ai/test/auth-storage-codex-selection.test.ts` — `yields an exhausted paid account over an idle free account for a paid-gated model` (:1953), `attempts every exhausted account for a paid-gated model until one passes the plan gate` (:1993), `routes codex spark to a single Plus account when no Pro is connected` (:2145), `does not reselect a pinned Spark credential with a legacy shared block` (:2667).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "oh-my-pi", query: "resolveOpenAICodexPlanRequirement", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the tri-state eligibility + confirm-before-enforce + three-pass degradation; adapt model/plan vocabularies; omit OpenAI token tables if host has no tiered models. Gating on unknown plans is the wrong port that locks out grandfathered accounts.
