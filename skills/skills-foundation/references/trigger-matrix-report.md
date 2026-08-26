<!-- capsule-v2 -->
# Trigger-Matrix Report — how does an optimization loop's history become a scannable per-query pass/fail grid?

**Source:** anthropics/skills (Apache-2.0) `main@3b3fad96`; Codebase Memory `skills`. **Question:** How does generate_report.py render every description attempt against every query, and what do the aggregate scores actually count?

## Iterations-as-rows, queries-as-columns, runs-aggregated cells
**Path/Symbol:** `skills/skill-creator/scripts/generate_report.py::generate_html` (:16–301, read whole; graph-resolved line-exact).
**Signature:** `generate_html(data: dict, auto_refresh=False, skill_name="") -> str`; CLI takes run_loop JSON via file or `-` (stdin).
**Data Shape:** rows = `data["history"]` entries (one per description attempt); columns = unique train queries from `history[0].train_results|results` then test queries from `history[0].test_results`, each column headed with its query text and a polarity class (`positive-col` should-trigger / `negative-col` should-not) + blue `test-col` tint. Cell lookup is by QUERY STRING: `train_by_query = {r["query"]: r for r in train_results}`.

### Decisive source
```python
# Compute aggregate correct/total runs across all retries
def aggregate_runs(results: list[dict]) -> tuple[int, int]:
    correct = 0
    total = 0
    for r in results:
        runs = r.get("runs", 0)
        triggers = r.get("triggers", 0)
        total += runs
        if r.get("should_trigger", True):
            correct += triggers          # want it to trigger
        else:
            correct += runs - triggers   # want it NOT to
    return correct, total
```
```python
if test_queries:
    best_iter = max(history, key=lambda h: h.get("test_passed") or 0).get("iteration")
else:
    best_iter = max(history, key=lambda h: h.get("train_passed", h.get("passed", 0))).get("iteration")
```

**Flow:** collect column set from FIRST history entry → render legend (should / shouldn't / train / test swatches) → one row per attempt: iteration number, polarity-colored score chips (≥0.8 good, ≥0.5 ok, else bad), monospace description, then ✓/✗ per query cell with tiny `triggers/runs` rate beneath → best row highlighted (test score wins when a holdout exists, else train).
**Invariant:** The aggregate counts RUNS, not queries — a 2/5 trigger rate on a positive query contributes 2 correct of 5, so flaky descriptions read as middling even when the binary pass flag says fail; the per-cell binary ✓/✗ uses the SEPARATE precomputed `pass` field. Test columns exist only if any entry carried test_results — the holdout's whole job is to catch overfitting that train columns would reward. Best-selection mirrors run_loop's own choice, so the report's highlight IS the applied description.
**Probe:** No upstream tests. Deterministic probes (anchors re-derived & byte-exact executed 2026-08-24): `grep -c 'correct += runs - triggers' skills/skill-creator/scripts/generate_report.py` = 1; plain-literal `grep -c 'th class="{polarity}' skills/skill-creator/scripts/generate_report.py` = 1 (:193 train header only; the :198 holdout header is `test-col {polarity}`) — a unified both-header count needs a regex engine that accepts `[a-z- ]*\{polarity\}` (python re finds 2; GNU grep -E rejects `[a-z- ]` as invalid range end on this host). Count train/holdout headers separately, or use grep -o with two fixed strings. ERRATUM: this capsule originally shipped the second anchor with a literal `…` ellipsis path — unexecutable as written; full repo-root-relative path restored.
**Coverage caveat:** pure rendering module; contract pinned to source lines.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "skills", query: "generate_html report history", limit: 5 });
// skills.skills.skill-creator.scripts.generate_report.generate_html Function generate_report.py 16-301
```

## Verdict
Adopt for any eval-loop reporting: matrix layout with polarity+holdout encoded in column classes, runs-aggregated scoring distinct from per-case pass flags, best-row = selection rule made visible. Adapt styling freely; keep the two-score separation (runs-rate vs case-pass). Omit the Google-Fonts dependency for offline hosts.
