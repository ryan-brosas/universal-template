<!-- capsule-v2 -->
# Retrieval envelope recommendation — how do you tell an LLM which scope to trust WITHOUT nudging it toward weak data?

**Source:** cuga-agent Apache-2.0 `main@5de53ade77c36166da6ace906af488b2b445454f`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** What are the exact thresholds for `prefer_<scope>` / `low_confidence` / `no_clean_results`, and why does the ratio rule need an absolute floor?

## Ratio 1.5× + absolute floor 0.5, low-confidence floor 0.3
**Path/Symbol:** `src/cuga/backend/knowledge/envelope.py:27-37` (thresholds), `:117-160` (`_compute_recommendation`), `:163-260` (`build_retrieval_envelope`).
**Signature:** `_compute_recommendation(top_score_by_scope: dict[str, float]) -> str | None`; `build_retrieval_envelope(*, results, scope_requested, multi_stats, single_stats, single_scope_name, filter_mode, fallback_from, include_scores) -> dict`.
**Data Shape:** Recommendation ∈ {`prefer_<scope>`, `low_confidence`, `no_clean_results`, None}; per-scope stats obey the invariant `candidates == returned + filtered + below_threshold + drain_drops + dedup_collapses`.

### Decisive source
```python
# envelope.py:27-31 — why the floor exists
# The absolute floor prevents the 1.5× ratio rule from firing when both
# scopes are low-confidence (e.g. 0.45 vs 0.30 — ratio fires but both
# are weak; we don't want to nudge the LLM toward weak data).
_RECOMMEND_RATIO = 1.5
_RECOMMEND_ABSOLUTE_FLOOR = 0.5
_LOW_CONFIDENCE_FLOOR = 0.3
```
Decision order: empty scored dict ⇒ None; winner `< 0.3` ⇒ `low_confidence` (hedge); single scope ⇒ None (no nudge); runner ≤ 0 ⇒ `prefer_<winner>` only if winner ≥ 0.5; else `prefer_<winner>` iff `winner >= 0.5 and winner/runner >= 1.5`. `no_clean_results` is decided at the CALL SITE (`candidates > 0 and returned == 0 and filtered > 0`) because score math can't run on an empty top-score dict. The envelope also carries a `reading_directive` string riding WITH the data (LLM reads it at answer-composition time, thousands of tokens after the system prompt), whose v2 encodes three post-fix corrections: answer-directly-first nudge, explicit by_source-vs-results scoping, and "lines[i+1] is the WRONG move" for stacked PDF label/value blocks (pair by POSITION).

**Flow:** search → chunks serialized once (`_result_to_chunk`, shared by HTTP route AND SDK client to prevent drift) → per-scope stats entries → totals sums → recommendation computed → envelope assembled with `by_source`/`scope_legend` ONLY for multi-scope searches; back-compat `filtered_count` emitted only when non-zero.
**Invariant:** Recommendations are emitted ONLY for unambiguous patterns (the LLM contract teaches it to read this field first — vague hints dilute it); both wire surfaces must build envelopes through this one module.

**Probe:** `tests/unit/test_knowledge_rag_scope_failure_fix.py::test_envelope_recommendation_prefer_scope_requires_abs_floor / _low_confidence_when_all_below_floor / _no_clean_results_when_all_filtered / test_sdk_and_http_envelopes_match_modulo_include_scores` — pins all three recommendations plus surface parity.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "build_retrieval_envelope compute_recommendation scope", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the threshold triple (1.5 ratio / 0.5 floor / 0.3 low-conf), call-site no_clean_results, and the data-riding reading directive pattern. Adapt thresholds via measurement on your score distributions. Omit by_source if you're single-scope.
