<!-- capsule-v2 -->
# Warm-start label rule — which pipeline outcomes become ML positives, and which terminal is the only negative?

**Source:** OpenOutreach GPL-3.0 `main@c3ac1434118ac5301b193506d1d01e6e313bc622`; Codebase Memory `openoutreach`. **Question:** When your label source is a workflow table rather than human annotations, how do you map row states to training labels without teaching the model the wrong lesson?

## Connected graph-selected seam
**Path/Symbol:** `openoutreach/crm/models/lead.py:Lead.get_labeled_arrays` (:107-155).
**Signature:** `get_labeled_arrays(cls, campaign) -> tuple[np.ndarray, np.ndarray]` — (X (n,384) float32, y int32); empty ⇒ `(np.empty((0,384)), np.empty(0, dtype=np.int32))`.
**Data Shape:** reads `Deal.values_list("lead_id", "state", "outcome")`; joins stored float32 embedding bytes back to rows; leads without embeddings are skipped.

### Decisive source
```python
for lid, state, outcome in deals:
    if state == DealState.FAILED:
        if outcome == Outcome.WRONG_FIT:
            label_by_lead[lid] = 0     # ONLY the LLM's own rejection is negative
    else:
        label_by_lead[lid] = 1         # incl. NO_EMAIL_BETTERCONTACT: fit positive,
                                       # only reachability failed
# Skipped: any other FAILED outcome (defensive — none are produced today)
```

**Flow:** campaign-scoped deal scan → state/outcome → per-lead dict (later deals overwrite: one lead = one current verdict) → embedding join → arrays for the GP warm start.
**Invariant:** The label is the LLM *fit* verdict, never the pipeline outcome. Because an enrichment miss owns its own terminal state (`NO_EMAIL_BETTERCONTACT`, not FAILED), "non-FAILED ⇒ 1" stays exact; if that miss were folded into FAILED, every unreachable-but-well-fitted lead would train the model against its own good judgment. The docstring records the retired mislabelling this shape prevents: reply outcomes once wrote non-FAILED terminations, so "not interested" replies trained as positives — resolved by deleting the outcome vocabulary.
**Probe:** `tests/ml/test_embeddings.py` — `test_get_labeled_arrays_empty` (:70-76), `test_get_labeled_arrays_from_deals` (:78-105, label set {0,1} from state+outcome), `test_get_labeled_arrays_keeps_no_email_miss_positive` (:107-124, the NO_EMAIL ⇒ 1 invariant verbatim), `test_get_labeled_arrays_skips_operational_failures` (:126-142, non-wrong_fit FAILED excluded).

## Get live surrounding code
```ts
await mcp.codebase_memory.search_graph({ project: "openoutreach", query: "get_labeled_arrays label wrong_fit embedding", limit: 10 });
```

## Verdict
Adopt: derive labels from (state, outcome) pairs with an explicit whitelist for negatives and everything-else-positive only when your terminal taxonomy makes that safe; keep unknown outcomes skipped-and-defensive rather than defaulted; return typed empty arrays instead of raising on a cold campaign. Adapt states to your schema; omit numpy byte plumbing.
