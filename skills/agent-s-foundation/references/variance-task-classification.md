<!-- capsule-v2 -->
# variance-task-classification — How does Best-of-N scoring decide which tasks a judge may grade?

**Source:** Agent-S MIT `main@bffdb59c`; Codebase Memory `ext-agent-s`. **Question:** How are tasks split into constant vs variance, and how is the final BoN score composed?

## Classification seam
**Path/Symbol:** `osworld_setup/s3/bbon/utils.py:get_new_tasks_classification` (:163-226), `check_selected_trajectory` (:229-265), `evaluate_comparative_results` (:268-301); round driver in `run_judge.py:run_experiment` (:154-177).
**Signature:** `get_new_tasks_classification(results_dirs) -> {constant, variance, minimum, optimal, expected_value}`.
**Data Shape:** results_dirs = N trajectory dirs; each holds `<domain>/<task_id>/result.txt` with a float score. Classification: all scores equal ⇒ constant; else variance.

### Decisive source
```python
common_tasks = set.intersection(*tasks_per_dir)      # only tasks run in EVERY trajectory
...
if all(r == results[0] for r in results):
    constant_tasks.append(domain_task)
    constant_tasks_scores.append(results[0])
else:
    variance_tasks.append(domain_task)
optimal_sum += max(results)
expected_value += sum(results) / len(results)
return {"constant": ..., "variance": ...,
        "minimum": sum(constant_tasks_scores),   # constants counted ONCE, not per trajectory
        ...}
# final score: data["score"]["actual score"] = minimum + gain   (run_judge.py :140-146)
```

**Flow:** intersect task sets across trajectories → classify by score equality → judge grades ONLY variance tasks comparatively (initial/final screenshots + fact captions per trajectory, integer answer 1..N) → for each judged task, check_selected_trajectory validates the selected path is inside the results roots (commonpath guard) and returns (selected_val, optimal_val=max) → gain = Σ selected over Σ optimal → actual = minimum + gain.
**Invariant:** (1) Constant tasks contribute their score exactly once via `minimum`; judging them would be wasted signal — they're excluded from the LLM's workload by construction. (2) Tasks missing from ANY trajectory are dropped entirely (intersection). (3) A judge answer outside 1..N or non-integer yields selected_trajectory=None which contributes NOTHING to gain (comparative_judge.py :140-147) — abstention is scored as zero progress, not as failure of optimal. (4) The commonpath guard prevents a corrupted/escaped selection from scoring.
**Probe:** `grep -n 'set.intersection' osworld_setup/s3/bbon/utils.py` → :179.
**Probe:** `grep -n '"actual score"' osworld_setup/s3/bbon/run_judge.py` → :145.
**Probe:** `grep -n 'os.path.commonpath' osworld_setup/s3/bbon/utils.py` → :241.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-agent-s", query: "get_new_tasks_classification variance optimal expected_value", limit: 5 });
```

## Verdict
Adopt equality-based variance classification with intersection prefiltering and additive constant+judged-gain scoring; adapt to your metric; omit nothing — the abstention-as-zero-progress rule keeps the judge honest under malformed answers.
