<!-- capsule-v2 -->
# run_evaluators ordered fan-out — how do you run N evaluators concurrently on one context while preserving input order and keeping failures out of the results list?

**Source:** pydantic-ai MIT `main@a5b5fb7a247f863599d61dfa9159bc2ebc786255` (pydantic_evals); Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai`. **Question:** A porter adding a "re-run these evaluators on this stored case" tool needs all evaluators to run concurrently (latency = slowest, not sum), the returned results to line up with the evaluator list the caller passed, and one crashing evaluator to appear as DATA (a failure record) instead of cancelling its siblings.

## Task-group fan-out with index-slot writes; two-phase partition
**Path/Symbol:** `pydantic_evals/pydantic_evals/online.py:run_evaluators` (:300-335); per-evaluator kernel `evaluators/_run_evaluator.py:run_evaluator` (cited by run-evaluator-failure-envelope); ordered-gather twin `_utils.py:task_group_gather` (cited by sync-eval-loop-repair).
**Signature:** `async def run_evaluators(evaluators: Sequence[Evaluator], context: EvaluatorContext) -> tuple[list[EvaluationResult], list[EvaluatorFailure]]`.
**Data Shape:** success slot = `list[EvaluationResult]` (one evaluator may yield MULTIPLE results — flattened into the shared list); failure slot = single `EvaluatorFailure` value. Return order of `all_results` follows evaluator input order, then per-evaluator result order.

### Decisive source
```python
results_by_index: dict[int, list[EvaluationResult] | EvaluatorFailure] = {}

async with anyio.create_task_group() as tg:
    async def _run(idx: int, evaluator: Evaluator) -> None:
        results_by_index[idx] = await run_evaluator(evaluator, context)   # index-SLOT write

    for i, evaluator in enumerate(evaluators):
        tg.start_soon(_run, i, evaluator)                                 # ALL concurrent

for i in range(len(evaluators)):                                          # reassemble IN ORDER
    result = results_by_index[i]
    if isinstance(result, EvaluatorFailure):
        all_failures.append(result)
    else:
        all_results.extend(result)                                        # multi-result flatten
```

**Flow:** every evaluator is started immediately in one task group (no semaphore, no sampling — this is the BLOCKING, SINKLESS twin of `_online.dispatch_evaluators`; docstring: "Useful for re-running evaluators from stored data"). Each task writes its outcome into a dict slot keyed by INPUT index — completion order is discarded by construction. A second sequential loop walks indices 0..N-1 and partitions each slot: `EvaluatorFailure` values go to `all_failures`, result lists are extended into `all_results`. Failure isolation is inherited from the single-evaluator kernel: `run_evaluator` catches ANY exception (including invalid output types and exhausted retries) and returns an `EvaluatorFailure` value, so nothing ever escapes into the task group to cancel siblings.
**Invariant:** four rules: (1) index-slot writes + ordered reassembly give input-order output from concurrent execution — appending to a shared list inside tasks would race on order; (2) failures are PARTITIONED, not interleaved — callers get two clean lists, never a mixed stream; (3) multi-result evaluators flatten positionally (their N results occupy their slot's place); (4) empty evaluator list returns `([], [])` — zero-task task groups are legal and need no special case.
**Probe:** `tests/evals/test_online.py::test_run_evaluators_with_failure` (:257-266): `[AlwaysTrue(), FailingEvaluator()]` → 1 result + 1 failure whose error_message contains 'Simulated evaluator failure' (sibling survived); `test_run_evaluators_multi_result` (:278-287): one MultiResultEvaluator → 3 results named {accuracy, score, label}; `test_run_evaluators_empty` (:269-275): `([], [])`; `test_run_evaluators_async_evaluator` (:290-298): async def evaluators work unchanged. Suite EXECUTED GREEN at pin this pass (see verification.md).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pydantic-ai", query: "run_evaluators results_by_index EvaluatorFailure", limit: 10, fields: ["signature", "name", "file"] });
```
Live check this pass: Codebase Memory MCP was unreachable in this session (stdio env reference unavailable at transport open); anchors confirmed by direct read of online.py :300-335 + test_online.py :246-298 at pin `a5b5fb7a` (zero drift, clean tree).

## Verdict
Adopt the index-slot-write + ordered-reassembly pair for any "run many independent async units, report in input order" kernel — it is three lines and makes ordering a construction-time property instead of a synchronization problem. Adopt the value-not-exception failure envelope at the leaf (run-evaluator-failure-envelope) so the fan-out layer can stay exception-free. Adapt: if your host has no anyio, the same shape works with asyncio.gather over a list of coroutines that each write `out[i]`. Omit the partition if your callers want a single mixed stream — but then you must document which element type means what. Coverage caveat: none — function read whole at pin.
