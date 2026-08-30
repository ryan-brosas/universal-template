<!-- capsule-v2 -->
# Acquisition phase machine — when must exploration be forbidden even though information gain is the goal?

**Source:** OpenOutreach GPL-3.0 `main@c3ac1434118ac5301b193506d1d01e6e313bc622`; Codebase Memory `openoutreach`. **Question:** How do you choose between exploiting the model's best guess and exploring its most confusing region — per call — when the positive class may be synthetic?

## Connected graph-selected seam
**Path/Symbol:** `openoutreach/core/ml/qualifier.py:BayesianQualifier.acquisition_mode` (:483-518), `acquisition_scores` (:520-533), `qualifier_for` (:593-628); `openoutreach/core/pipeline/top_up.py:_advance` (:61-88).
**Signature:** `acquisition_mode() -> "exploit (p)" | "explore (BALD)" | None`; `qualifier_for(campaign) -> BayesianQualifier`.
**Data Shape:** mode None = unfittable; scores = predict_probs (exploit) or compute_bald (explore) over the candidate pool.

### Decisive source
```python
if not self._fit_if_needed(): return None
if self.is_cold:
    return "exploit (p)"                    # cold: ALWAYS exploit, balance is uninformative
n_neg, n_pos = self.class_counts
return "exploit (p)" if n_neg > n_pos else "explore (BALD)"

# qualifier_for(): rebuilt where needed, never resident
X, y = Lead.get_labeled_arrays(campaign)
if len(X) > 0: qualifier.warm_start(X, y)
anchors = stored_anchors(campaign) if qualifier.has_real_positive else ensure_anchors(campaign)
```

**Flow:** top_up asks the mode → exploit prefers gate-clearing candidates (falls back to best-any for the free label, then to discovery when nobody qualifies) → explore labels max-BALD with NO confidence gate → both converge through run_qualification, whose verdict is always the LLM's.
**Invariant:** During the cold phase the class balance has ZERO information — anchors are held at the shortfall so `n_neg > n_pos` is false by construction — and BALD would spend every call on the lead the model is most confused about, i.e. least like the ICP (live evidence: four consecutive BALD picks at P≈0.25–0.42 were veterinary services, cybersecurity education, K-12 tutoring and a metaverse PM against a health-and-wellness ICP — every rejection accurate, none a step toward a first acceptance). The gate rations the *paid credit*, never the free LLM label: an explore branch without a confidence filter and an exploit fallback that labels below-gate leads are what keep discovery+labelling from deadlocking. The qualifier is built where needed and dropped (`qualifier_for`) because a resident model silently goes stale — a daemon fitting at boot wouldn't move its posterior for labels written an hour later.
**Probe:** `tests/ml/test_qualifier.py::TestColdPhaseAcquisition` (:328+), `tests/test_qualify.py` (balance-driven selection + degraded path).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "openoutreach", query: "acquisition_mode", limit: 5 });
```

## Verdict
Adopt the phase test (synthetic-share-of-positive-class) as the acquisition axis override; adopt balance-driven explore/exploit afterwards; adopt build-per-pass qualifier construction over warm resident models. Adapt what "cold" means for your label source; omit pydantic_ai Agent plumbing inside qualify_with_llm beyond its structured-output shape.
