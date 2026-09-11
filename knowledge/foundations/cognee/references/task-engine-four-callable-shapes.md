<!-- capsule-v2 -->
# Task engine — how do four callable shapes stream through one pipeline contract?

**Source:** cognee (Apache-2.0) `main@a8f9760b`; Codebase Memory `ext-cognee`. **Question:** How does a pipeline task wrapper normalize coroutine / sync-function / generator / async-generator tasks into a uniform batched async-iterator interface, and which sentinel drops an item?

## Task: type-dispatched execution with batched yields
**Path/Symbol:** `cognee/modules/pipelines/tasks/task.py:Task.__init__` (:187-224), `execute_*` (:251-302), `execute` (:304-309).
**Signature:** `Task(executable, *args, task_config=None, batch_size=None, enriches=False, **kwargs)`; `async execute(args, kwargs, next_batch_size=None)` (yields lists for generator tasks, single items for coroutines/functions).
**Data Shape:** `task_config["batch_size"]` defaults to 1 and is injected if a custom dict omits it; `default_params = {"args": args, "kwargs": kwargs}` are merged at `run()` time (`combined_args = args + self.default_params["args"]`, `{**defaults_kwargs, **kwargs}` — call-time kwargs win). `accepts_ctx` cached at construction via `"ctx" in inspect.signature(...)`.

### Decisive source
```python
if inspect.isasyncgenfunction(executable):   # dispatch order matters:
    self._execute_method = self.execute_async_generator
elif inspect.isgeneratorfunction(executable):
    self._execute_method = self.execute_generator
elif inspect.iscoroutinefunction(executable):
    self._execute_method = self.execute_coroutine
elif inspect.isfunction(executable):         # plain sync fn → yield-once
    self._execute_method = self.execute_function

# generator tasks accumulate into batches:
async for partial_result in async_iterator:
    if isinstance(partial_result, _Drop): continue
    results.append(partial_result)
    if len(results) == batch_size:
        yield results; results = []
if results: yield results

# coroutine/function tasks yield ONE item, with the enriches passthrough:
task_result = await self.run(*args, **kwargs)
if isinstance(task_result, _Drop): return
if self.enriches and task_result is None:
    yield args[0] if args else None; return     # pass input through unchanged
yield task_result
```

**Flow:** `execute()` receives the NEXT task's batch_size (`run_tasks_base` :280: `next_task_batch_size`) so upstream generators emit batches sized for the downstream consumer → `handle_task` iterates `running_task.execute(args, kwargs, next_task_batch_size)`.
**Invariant:** Generator-shaped tasks yield BATCHES (lists); coroutine/function tasks yield SINGLE items — a porter who makes both yield batches breaks every downstream consumer that treats one result as one item. `_Drop` (from `cognee.pipelines.types`) is filtered in all four executors; `enriches=True` is what lets an enrichment task return None and still keep the item flowing.
**Probe:** `cognee/tests/unit/pipelines/test_bound_task_pipeline.py::TestTaskSpec` / `TestBoundTask.test_bound_task_enriches_override` / `TestDropWithTaskSpec.test_drop_works_in_task`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-cognee", query: "Task execute_coroutine _Drop enriches batch_size generator", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the dispatch ladder + next-task-batch-size handshake + _Drop/enriches semantics as-is; adapt batch accumulation to your streaming runtime; omit the BoundTask/TaskSpec deferred-call sugar (`task(fn)(**kw)` → `with_config` merge) unless you also port `run_pipeline(steps)`.
