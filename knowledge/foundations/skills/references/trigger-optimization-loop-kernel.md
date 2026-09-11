<!-- capsule-v2 -->
# Trigger optimization loop kernel — how does a best-of-N description optimizer stay honest about generalization?

**Source:** anthropics/skills (Apache-2.0) `main@3b3fad96`; Codebase Memory `skills`. **Question:** What is the exact state machine of the eval→improve loop — how are train/test split, history blinding, exit conditions, and best-attempt selection wired so the optimizer cannot overfit or grade itself on data it saw?

## Loop state machine (`run_loop.py`, whole file)
**Path/Symbol:** `skills/skill-creator/scripts/run_loop.py` — `split_eval_set` (:24–44), `run_loop` (:47–241), `main` (:244–324).
**Signature:** `run_loop(eval_set, skill_path, description_override, num_workers, timeout, max_iterations, runs_per_query, trigger_threshold, holdout, model, verbose, live_report_path=None, log_dir=None) -> dict`; `split_eval_set(eval_set, holdout, seed=42) -> tuple[list, list]`.
**Data Shape:** eval entries `{query, should_trigger}`; per-run results carry `{query, pass, triggers, runs, should_trigger}`; returned dict: `exit_reason, original_description, best_description, best_score, best_train_score, best_test_score, final_description, iterations_run, holdout, train_size, test_size, history`.

### Decisive source
```python
# :194-198 — the improvement model NEVER sees test scores
blinded_history = [
    {k: v for k, v in h.items() if not k.startswith("test_")}
    for h in history
]
# :216-222 — selection is by TEST score when a holdout exists
if test_set:
    best = max(history, key=lambda h: h["test_passed"] or 0)
else:
    best = max(history, key=lambda h: h["train_passed"])
```

**Flow:** stratified split once up front (`random.seed(42)`; shuffle positive and negative groups separately; `max(1, int(n*holdout))` per polarity guarantees ≥1 test query of EACH polarity, default holdout 0.4) → per iteration: evaluate train+test in ONE `run_eval` batch for parallelism, then re-split results by query-string set membership → append full history entry (test keys plus backward-compat train mirror keys `passed/failed/total/results` for the report generator) → rewrite live HTML report with `best_score: "in progress"`, auto-refresh on → exit if **train** failures hit zero (`all_passed (iteration N)`), else exit at `max_iterations`, else improve on blinded history → after the loop pick best by TEST score (`or 0` guards `None`), fall back to train score only with no holdout.
**Invariant:** The split is fixed ONCE before iterating (no re-shuffling per iteration); blinding is structural — `improve_description` receives only non-`test_` keys, so no prompt engineering can leak holdout results into the next proposal; early exit is gated on TRAIN passing, but the shipped `best_description` is still chosen by TEST, which can be an EARLIER iteration than the final one.
**Probe:** No upstream tests exist repo-wide. Deterministic + behavioral (executed this pass):
`python3 -c "import sys; sys.path.insert(0,'$REFERENCE_ROOT/skills/skills/skill-creator'); from scripts.run_loop import split_eval_set; tr,te=split_eval_set([{'query':str(i),'should_trigger':i%2==0} for i in range(10)],0.4); print(len(tr), len(te), sorted({e['should_trigger'] for e in te}))"`
→ prints `6 4 [False, True]` (holdout sizes AND both polarities present in test = stratification invariant; package root is the skill-creator dir since modules import `from scripts.…`). Blinding anchor:
`grep -c 'not k.startswith("test_")' skills/skill-creator/scripts/run_loop.py` = 1.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "skills", query: "run_loop split_eval_set blinded history", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt: fixed seeded stratified holdout with one-polarity-minimum, single-batch evaluation re-split by query identity, key-prefix history blinding, train-gated exit / test-selected winner. Adapt: defaults (workers=10, timeout=30s, iterations=5, runs_per_query=3, threshold=0.5, holdout=0.4) to your harness scale. Omit: the webbrowser-open live report and temp-file naming (UX surface); the backward-compat duplicated train keys exist only for generate_report compatibility. Caveat: no upstream tests; claims pinned by direct source read + executed probes above.
