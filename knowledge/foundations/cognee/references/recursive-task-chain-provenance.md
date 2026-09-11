<!-- capsule-v2 -->
# Recursive task chain — why does the pipeline recurse per result instead of looping?

**Source:** cognee (Apache-2.0) `main@a8f9760b`; Codebase Memory `ext-cognee`. **Question:** How are N tasks chained so each intermediate result (including every batch from a generator task) flows through the remaining tasks exactly once, with provenance stamped at the right stage?

## run_tasks_base / handle_task
**Path/Symbol:** `cognee/modules/pipelines/operations/run_tasks_base.py:run_tasks_base` (:264-285), `handle_task` (:151-261), `_stamp_provenance` (:34-118).
**Signature:** `async run_tasks_base(tasks, data=None, user=None, ctx=None)` — async GENERATOR; `handle_task(running_task, args, leftover_tasks, next_task_batch_size, user, ctx)`.
**Data Shape:** `args = [data] if data is not None else []`; recursion state is `tasks[0]` + `tasks[1:]`; empty task list yields the data itself (`if len(tasks)==0: yield data; return`) which is what terminates the chain.

### Decisive source
```python
# handle_task, inside `with new_span(...)`:
async for result_data in running_task.execute(args, kwargs, next_task_batch_size):
    ...
    # recurse into the REMAINING tasks for EACH result:
    async for result in run_tasks_base(leftover_tasks, result_data, user, ctx):
        yield result
```

**Flow:** For each result a task produces, the leftover list runs to completion before the next result is pulled — a generator task emitting 3 batches drives downstream tasks 3×, interleaved. Provenance stamping happens on each result BEFORE the recursive hand-off.
**Invariant:** The recursion (not a loop) is load-bearing: it preserves streaming order per item/batch and makes the terminal `yield data` the natural end-of-chain. `_stamp_provenance` only sets fields that are None (first writer wins), reuses a `visited` set of `id()`s persisted on `ctx._provenance_visited` across stages so already-stamped DataPoints are skipped, and stamps `topological_rank = task_index+1` ONLY when current rank is None or 0 (0 treated as unset) and only when `ctx` exists. Errors propagate after span/telemetry bookkeeping (`raise error` — never swallowed).
**Probe:** `cognee/tests/unit/modules/pipelines/test_provenance_stamping.py::test_stamp_provenance_does_not_overwrite_existing`, `test_stamp_provenance_no_infinite_recursion`; `test_topological_rank_stamping.py::test_visited_set_prevents_rerank_in_later_task`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-cognee", query: "_stamp_provenance topological_rank source_pipeline visited", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the recursive chain + first-writer-wins stamping + cross-stage visited-set; adapt the DataPoint field names and rank sentinel to your model; omit cognee's telemetry/span calls (host-specific observability).
