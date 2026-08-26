<!-- capsule-v2 -->
# Real-DDL plan-evidence gate — what five conditions MUST hold before an advisor may keep a freshly built index?

**Source:** teable AGPL-3.0 `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** After the executor has actually created a search-vector column+index, how does real-DDL validation decide keep vs cleanup?

## EXPLAIN-after + bidirectional EXCEPT equivalence + strict assertion ladder
**Path/Symbol:** `packages/v2/adapter-table-query-ops-postgres/src/searchVector.ts` — `validateRealDdlSearchVectorPlan` (:2406-2443), `assertRealDdlPlanEvidenceReady` (:2445-2477), `validateSubstringResultCompatibility` (:2726-2756), `chooseNextAction` (:2834-2852), `explainCostDeltaPct` (:2816-2823).
**Signature:** `validateRealDdlSearchVectorPlan(db, input): Promise<TableQuerySearchVectorPlanEvidence>`; throwing gate `assertRealDdlPlanEvidenceReady(evidence, indexName): void`.
**Data Shape:** evidence `{explainStatus:'validated'|'skipped'|'failed', explainMethod:'real_index', costBefore/After, costDeltaPct, planNodeBefore/After, usesCandidateIndex (after.indexName === indexName), semanticsCompatible: boolean}`; next-action vocabulary `'manual_investigation'|'no_index_change'|'needs_plan_validation'|'candidate_not_recommended'|'ready_for_confirmation'`.

### Decisive source
```ts
// EXCEPT both directions on ctid = set equality of baseline ILIKE vs generated-column query:
SELECT NOT EXISTS (
  (SELECT ctid FROM t WHERE $baseline EXCEPT SELECT ctid FROM t WHERE $optimized)
  UNION ALL
  (SELECT ctid FROM t WHERE $optimized EXCEPT SELECT ctid FROM t WHERE $baseline)
) AS compatible
// optimized = document LIKE lower(pattern) AND (original ILIKE OR-chain)   ← belt-and-suspenders
// the gate — every failure is a THROW that triggers upstream managed-object cleanup:
if (!evidence.usesCandidateIndex)      throw new Error(`...did not use index ${indexName}`);
if (evidence.semanticsCompatible !== true) throw new Error('...did not preserve ILIKE results');
if (!Number.isFinite(costDeltaPct) || costDeltaPct >= 0) throw new Error('...did not improve plan cost');
```
**Flow:** before-plan captured BEFORE DDL → after build: EXPLAIN the optimized predicate (generated column ANDed with the original exact ILIKE chain so correctness never depends on the new object alone), verify the plan actually picked the candidate index (`usesCandidateIndex` by name), run the two-direction EXCEPT probe for result-set equality with the baseline, compute % cost delta → the assertive gate demands ALL of validated / real_index method / used-candidate / semantics-preserved / strictly-negative cost delta — any miss throws into the executor's `rethrowAfterManagedObjectCleanup`, dropping the half-proven objects.
**Invariant:** "faster" alone is never enough and "equivalent" alone is never enough — BOTH must be proven against the LIVE table before the advisor keeps real DDL; the compatibility SQL is symmetric (EXCEPT in both directions UNION ALL'd) so extra rows either way fail; cost improvement must be STRICTLY negative percent. Hypothetical-mode recommendations use a parallel ladder (`chooseNextAction`: unvalidated ⇒ `needs_plan_validation`, <20% improvement or unused candidate ⇒ `candidate_not_recommended`) instead of throws because nothing was built yet.
**Probe:** `src/searchVector.spec.ts::describe('assertReadySearchVectorExecutionRecommendation')` `"allows real-DDL validation mode to accept a current candidate"` (:54) + `describe('chooseScopedExpressionNextAction')` it.each matrix (:134-171) pinning ready_for_confirmation / candidate_not_recommended / needs_plan_validation branches.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "validateRealDdlSearchVectorPlan assertRealDdlPlanEvidenceReady validateSubstringResultCompatibility", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the five-condition keep-gate over live evidence, symmetric EXCEPT equivalence probes, optimized-predicate-with-exact-fallback construction, and the throw-to-cleanup linkage for real DDL (vs reason-codes for hypotheticals). Adapt thresholds (20% floor). Omit teable's specific next-action enum names if your state machine differs.
