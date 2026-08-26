<!-- capsule-v2 -->
|# Record-escalation candidate plan — how does a chunk-returning search tool teach the model WHEN fetching a whole record is worth it?

**Source:** pipeshub-ai Apache-2.0 `main@68509725e15c`; Codebase Memory project `pipeshub-ai`. **Question:** Search returns excerpts, but some questions need the full document — what deterministic per-call computation turns held-vs-total block counts into a fetch nudge the model can act on?

## Coverage over ALL accumulated results → relevance-ordered candidate plan → two-placement render
**Path/Symbol:** `backend/python/app/agents/actions/retrieval/retrieval.py` :579–648 (plan construction + stash); `backend/python/app/modules/agents/record_escalation/coverage.py` `analyze_coverage` (:30–81); `policy.py` `build_candidates` (:138–203); `renderer.py` `render_candidate_table` (:69–144) + `render_coverage_note` (:41–66).
**Signature:** `analyze_coverage(flattened_results, virtual_record_id_to_result) -> dict[record_id, (blocks_held, blocks_total)]`; `build_candidates(*, coverage, records_in_relevance_order, already_fetched_ids, max_candidates=8) -> FetchPlan`.
**Data Shape:** coverage values are `(held distinct countable block indices, total countable blocks)` over the SAME block set so `held==total ⇔ complete`; FetchPlan carries `candidates: tuple[FetchCandidate]` + log-only `excluded: tuple[(id, reason)]`.

### Decisive source
```python
# retrieval.py — runs REGARDLESS of needs_whole_document:
# Runs regardless of needs_whole_document: the counts ("you have 4 of 87
# blocks") are the only way the model can tell whether reading further would
# add anything ... The signal only chooses the header's framing.
all_final = self.state.get("final_results", [])          # ACCUMULATED pool
coverage = analyze_coverage(all_final, full_vr_map)
plan = build_candidates(coverage=coverage,
                         records_in_relevance_order=records_in_order,  # pre-sort!
                         already_fetched_ids=already_fetched)
self.state["fetch_coverage"] = coverage; self.state["fetch_plan"] = plan

# renderer.py — placement is the design:
# render_coverage_note → one line at the TOP ("see the candidate list at the
#   end"), because the table "lives at the bottom, potentially thousands of
#   tokens away"; returns "" when coverage is high and nothing needs whole-doc.
# render_candidate_table → CTA leads BEFORE rows when needs_whole_document or
#   low coverage; drops the "is it relevant" re-check on the whole-doc path.
```
(retrieval.py :584–628; renderer.py docstrings :52–68/:84–96.)

**Flow:** merge this call's blocks into state → recompute coverage globally → walk records in upstream RELEVANCE order (deduped, ≤8, skipping already-fetched and complete records with log-only reasons) → stash plan on state for observability → render note (top) + table (bottom) around the `<record>` blocks.
**Invariant:** (1) Coverage is computed over the WHOLE accumulated pool so parallel calls report global counts, never per-call partials. (2) Candidate order follows relevance ranking — the display sort by (virtual_record_id, block_index) happens LATER (:661–664) and must not precede plan build. (3) The plan is unconditional; only framing varies — withholding counts removes the model's ability to judge a fetch. (4) Exclusion reasons are logging-only, never model-visible. (5) Unknown totals render as "document length unknown", never as full coverage.
**Probe:** EXECUTED at pin: test_retrieval.py::TestNavigateTip + summaries suite pin tail composition; record_escalation suites pin the kernel: test_kernel.py TestBuildCandidates.test_relevance_ordering_preserved :200–207, test_fragment_blocks_not_counted_in_total :81–91, TestRenderCandidateTable.test_unknown_total_is_never_shown_as_full_coverage :429–454; test_renderer.py TestCoveragePct zero/negative guards :37–50.
**Retrieve:** EXECUTED live — mcp__codebase-memory__search_graph project=`pipeshub-ai` query="record escalation fetch candidates coverage blocks held total relevance order" → rank-1 kernel test pins blocks-held/total rendering; rank-5 resolves policy.build_candidates; ranks 2–10 cover coverage counting + renderer guard tests.

## Verdict
Adopt the coverage→plan→two-placement pipeline for any excerpt-returning tool with a fetch-more primitive. Adapt countable-block accounting to your chunk identity and the ≤8 cap to your context budget. Omit the top-note ONLY if your results are short enough that the footer table is reliably read.

<!-- capsule-evidence: pipeshub-ai@68509725e15c retrieval.py L579–648; record_escalation/{coverage,policy,renderer}.py via get_code_snippet; direct suites test_kernel/test_renderer/test_policy; live search_graph 2026-08-26 -->
