<!-- capsule-v2 -->
# Additive risk-score ladder — how do you turn one observation window into a bounded, explainable risk level?

**Source:** teable AGPL `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** How does a pure policy object convert observation + physical stats + index inspection + plan validation into a recommendation decision without thresholds hidden in call sites?

## Ten independent rules, additive scores, capped at 100
**Path/Symbol:** `packages/v2/table-query-ops/src/domain.ts`: `TableQueryRiskPolicy.evaluate` (:971-1035), `riskRule` (:1042-1046), `riskLevelFromScore` (:1309-1315), `defaultTableQueryRiskPolicyConfig` (:883-892), `TableQueryRiskReport.shouldRecommend` (:947-949), `buildRemediationCandidates` (:1317-1355).
**Signature:** `evaluate(input: {observation, physicalStats, indexInspection, planValidation?}): Result<TableQueryRiskReport, DomainError>`.
**Data Shape:** config: slow=3000ms, critical=10000ms, minRequests=5/window, highRiskTimeouts=3, largeTable=50k rows, wideSearch=30 fields, fanout=3, policyVersion=`table-query-risk-v1`. Rule scores: critical_latency 30, timeout_burst 25, missing/abnormal_index 20, high_latency/large_table/wide_search 15, expensive_filter/sort/fanout 10. Levels: ≥85 critical, ≥60 high, ≥35 medium, >0 low, 0 none.

### Decisive source
```ts
const matchedRules = [
  riskRule(observation.maxDurationMs() >= cfg.criticalThresholdMs, 'critical_latency', 30),
  riskRule(max < critical && max >= slow, 'high_latency', 15),   // mutually exclusive by construction
  riskRule(observation.timeoutCount() >= cfg.highRiskTimeouts, 'timeout_burst', 25),
  // … large_table / wide_search / expensive_filter(≥2 conditions AND slowCount>0) /
  //    expensive_sort(sortFields excluding tieBreakers) / aggregation_fanout
  riskRule(indexInspection.hasMissingUsefulIndex(), 'missing_useful_index', 20),
  riskRule(indexInspection.hasAbnormalIndex(), 'abnormal_index', 20),
].filter(Boolean);
const cappedScore = Math.min(100, matchedRules.reduce((s, r) => s + r.score, 0));
```

**Flow:** evaluate → collect matched rules (each rule independently true/false; latency rules written to be mutually exclusive) → sum + cap → level from score → report.create validates score∈[0,100] → candidates built from missing-index list (`gin_trgm→create_search_index`, sort-member→`create_sort_index`, else `create_filter_index`), abnormal→`repair_index`, empty→`manual_investigation` fallback so a risky query ALWAYS yields at least one candidate → handler recommends only when `shouldRecommend()` (= level not in {none, low}).
**Invariant:** Score is additive and explainable — every point traces to a named reason code carried on the report; the cap prevents double-matched catastrophes from saturating; `policyVersion` is stamped onto every report/recommendation so threshold changes invalidate old open recommendations instead of silently re-scoring them.
**Probe:** `domain.spec.ts:192` "raises risk and recommends phase 1 index remediation for slow wide search"; :289 advisor matrix describe block; :225 "keeps plan validation evidence in the risk report snapshot".
**Coverage caveat:** none — direct specs incl. an advisor matrix suite.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "TableQueryRiskPolicy evaluate riskRule buildRemediationCandidates", limit: 8, fields: ["signature","name","file"] });
```

## Verdict
Adopt the additive-reasons-then-cap pattern and the policy-version stamping (it is what makes persisted recommendations safe across deploys); adapt rule set/scores to your workload; omit teable's specific thresholds.
