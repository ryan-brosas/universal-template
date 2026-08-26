<!-- capsule-v2 -->
# fact-caption-pipeline — How are per-step change captions generated at scale with resume?

**Source:** Agent-S MIT `main@bffdb59c`; Codebase Memory `ext-agent-s`. **Question:** How does the offline fact-caption pipeline parallelize judge calls and skip finished work?

## Caption pipeline seam
**Path/Symbol:** `osworld_setup/s3/bbon/generate_facts.py:generate_fact_captions_parallel` (:59-142), `main` (:145-211).
**Signature:** `generate_fact_captions_parallel(task_dir, judge, step_semaphore=None) -> List[str]`; env knobs `DIFFCAP_PER_STEP_CONCURRENCY` (default 100) and `DIFFCAP_PER_TASKDIR_CONCURRENCY` (default 4).
**Data Shape:** Inputs per task_dir: `step_*.png` sequence (numeric-sorted) + optional `traj.jsonl` (per-step exec_code). Output: `fact_captions.jsonl` with one `{fact_thoughts, fact_answer, screenshot_num}` record per step pair.

### Decisive source
```python
if "fact_captions.jsonl" in os.listdir(task_dir):   # resume: file-existence gate
    print(f"Fact captions already exist for {task_dir}"); continue
...
shared_step_semaphore = asyncio.Semaphore(per_step)     # global cap across ALL dirs
taskdir_semaphore = asyncio.Semaphore(per_taskdir)      # per-dir cap
async def run_one(task_dir):
    async with taskdir_semaphore:
        return await generate_fact_captions_parallel(task_dir, judge, step_semaphore=shared_step_semaphore)
results = await asyncio.gather(*[run_one(d) for d in task_dirs], return_exceptions=True)
...
results = await asyncio.gather(*bounded_tasks, return_exceptions=True)  # step-level too
for i, result in enumerate(results):
    if isinstance(result, Exception): print(...); continue    # failed steps skipped, not fatal
```

**Flow:** classify new task dirs → skip any already holding fact_captions.jsonl → per dir, sort screenshots by embedded step number → for each adjacent pair load exec_code from traj.jsonl (missing ⇒ ValueError for that step) → run BehaviorNarrator.judge via asyncio.to_thread under BOTH semaphores → write surviving records in ONE pass.
**Invariant:** (1) Two-level concurrency control: a SHARED step semaphore bounds total LLM calls fleet-wide while a per-taskdir semaphore bounds directory fan-out. (2) return_exceptions=True + per-index filtering means individual caption failures never abort the batch; the jsonl is written only from successes (so a rerun after partial failure re-attempts only whole dirs, not steps). (3) Blocking PIL/cv2/LLM work moves off the loop via asyncio.to_thread; the judge itself is synchronous. (4) Screenshot ordering must parse `step_<n>` ints — lexicographic sort would misorder step_10.
**Probe:** `grep -n 'DIFFCAP_PER_STEP_CONCURRENCY\|DIFFCAP_PER_TASKDIR_CONCURRENCY' osworld_setup/s3/bbon/generate_facts.py` → :160-161.
**Probe:** `grep -c 'return_exceptions=True' osworld_setup/s3/bbon/generate_facts.py` → 2 (:117 step-level + :199-201 taskdir-level).
**Probe:** `grep -n 'asyncio.to_thread' osworld_setup/s3/bbon/generate_facts.py` → :47 (judge off-loop; run_judge.py has its own at :69).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-agent-s", query: "generate_fact_captions_parallel semaphore", limit: 5 });
```

## Verdict
Adopt two-level semaphores + file-existence resume + exception-tolerant gathers for batch media-caption pipelines; adapt naming conventions; omit nothing — writing only successful records is what keeps reruns idempotent at dir granularity.
