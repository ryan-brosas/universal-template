<!-- capsule-v2 -->
# Custom rule tier precedence — how do user-supplied rules override heuristics AND the classifier?

**Source:** pi-model-router MIT `main@002b48f9bb03c068e0ef97eb230f49df57a24f93`; Codebase Memory `pi-model-router`. **Question:** When several user rules match one prompt, which wins, and how far does that win propagate downstream?

## Rule matching inside the decision kernel
**Path/Symbol:** `extensions/routing.ts:decideRouting` rule block (lines ~186–224) + consumer gate `extensions/provider.ts:streamSimple` (lines 292–299).
**Signature:** rules: `RoutingRule[]` with `{ matches: string | string[]; tier: RouterTier; reason?: string }`.
**Data Shape:** `matches` is normalized to an array and lowercased per evaluation; the prompt is already lowercase. Outcome flags live on the decision: `isRuleMatched: true`, tier = winning rule's tier.

### Decisive source
```ts
for (const rule of rules) {
  const matches = Array.isArray(rule.matches) ? rule.matches : [rule.matches];
  const lowercaseMatches = matches.map((m) => m.toLowerCase());
  if (containsAny(prompt, lowercaseMatches)) {
    if (!highestTier || tierRank[rule.tier] > tierRank[highestTier]) {
      highestTier = rule.tier;   // tierRank = { low: 1, medium: 2, high: 3 }
      winningRule = rule;
    }
  }
}
...
decision.isRuleMatched = isRuleMatched;
```
```ts
// provider.ts — classifier runs ONLY when no pin, no rule win, no budget breach:
if (state.currentConfig.classifierModel && !pinnedTier &&
    !decision.isRuleMatched && !isBudgetExceeded) { ... runClassifier(...) }
```

**Flow:** collect ALL matching rules → keep the single highest-tier match (later equal-tier rules do not displace the first winner) → set phase via `phaseForTier(tier)` → use `rule.reason ?? "Matched custom routing rule for: <matches>"`. Downstream in the provider, `isRuleMatched` makes the LLM classifier skip entirely — a rule win is final for the turn.
**Invariant:** A matched rule beats every heuristic branch below it and cannot be overridden by the classifier; only a manual pin outranks it (pins are checked before rules).
**Probe:** `extensions/routing.test.ts` :248–271 ("should match custom rule first" asserts `isRuleMatched === true` and custom reason), :273–299 (case-insensitive `'Force-High'` vs prompt `force-high`), :301–328 (`summarize the refactor` matches low+high rules → high wins).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-model-router", query: "RoutingRule matches tierRank highest", limit: 10 });
```

## Verdict
Adopt highest-tier-wins over case-insensitive substring matching plus the classifier-suppression flag as one atomic contract; adapt the rule schema fields to your config surface; omit the `/router-pin` interaction that produces the even-higher pin precedence unless you port commands too. Note: the provider-side skip gate (:292–299) has no dedicated upstream test at this commit — pinned here from source.
