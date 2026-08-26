<!-- capsule-v2 -->
# Selected-models self-heal — how do per-profile model selections survive config churn without pinning dead models?

**Source:** Continue (Apache-2.0) `main@5522c6f44ca0ac3528b37244818fbfa39b5af470`; Codebase Memory `continue`. **Question:** When a user's saved role→model picks no longer exist in a freshly compiled config, how do you re-bind selections honestly and persist only what changed?

## Rectify ladder over GlobalContext selections
**Path/Symbol:** `core/config/selectedModels.ts:rectifySelectedModelsFromGlobalContext` (lines 10–80); called from `core/config/profile/doLoadConfig.ts:192`.
**Signature:** `rectifySelectedModelsFromGlobalContext(continueConfig: ContinueConfig, profileId: string): ContinueConfig`.
**Data Shape:** GlobalContext key `selectedModelsByProfileId: Record<profileId, Record<role, title | null>>` stores STRINGS; config carries `modelsByRole` (ILLM arrays) and `selectedModelByRole`. Roles walked in fixed order `[autocomplete, apply, edit, embed, rerank, chat]` — summarize deliberately excluded ("not implemented yet").

### Decisive source
```ts
for (const role of roles) {
  let newModel: ILLM | null = null;
  const currentSelection = currentForProfile[role] ?? null;
  if (currentSelection) {
    const match = continueConfig.modelsByRole[role].find((m) => m.title === currentSelection);
    if (match) newModel = match;              // 1) honor stored pick by exact TITLE
  }
  if (!newModel && continueConfig.modelsByRole[role].length > 0) {
    newModel = continueConfig.modelsByRole[role][0];   // 2) else first-model fallback
  }
  if (!(currentSelection === (newModel?.title ?? null))) fellBack = true;
  // Currently only check for configuration status for apply
  if (role === "apply" && newModel?.getConfigurationStatus() !== LLMConfigurationStatuses.VALID) {
    continue;                                  // 3) apply-role VALID gate: leave selection unwritten
  }
  configCopy.selectedModelByRole[role] = newModel;
}
if (fellBack) {                                // 4) rewrite shared state ONLY when it drifted
  globalContext.update("selectedModelsByProfileId", {
    ...currentSelectedModels,
    [profileId]: Object.fromEntries(
      Object.entries(configCopy.selectedModelByRole).map(([key, value]) => [key, value?.title ?? null])),
  });
}
```

**Flow:** read profile slice → per role: stored-title match → first-model fallback → drift flag → apply-only validity veto → write selection → after loop, rewrite GlobalContext iff any role drifted.
**Invariant:** a stored pick is honored only while a model with that EXACT title still exists; the apply role never gets an invalid-config model written (stale value survives instead), and GlobalContext is rewritten at most once per load and only when resolution diverged — no write amplification on steady state.
**Probe:** `core/config/profile/doLoadConfig.vitest.ts:49–51` mocks this fn as identity, proving it sits on every load's hot path; behavioral probe (source-pinned): empty GlobalContext selections plus two chat models resolve role selections to `modelsByRole.chat[0]` without a second-load rewrite. Runner block: vitest not installed repo-wide (see work record).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "continue", query: "rectifySelectedModelsFromGlobalContext", limit: 5 });
await mcp.codebase_memory.trace_path({ project: "continue", function_name: "continue.core.config.selectedModels.rectifySelectedModelsFromGlobalContext", direction: "inbound", depth: 2 });
// observed inbound: doLoadConfig tail (core/config/profile/doLoadConfig.ts:192) + its vitest mock
```

## Verdict
Adopt the match→fallback→drift-flag→persist-only-on-drift ladder for any "remembered selection over rotating inventory" problem; adapt the role list and validity gate to your domain roles; omit the GlobalContext singleton (any per-profile KV store works). Trap: `{...config}` shares `selectedModelByRole`, so writes mutate the INPUT config object.
