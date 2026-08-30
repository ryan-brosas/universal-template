<!-- capsule-v2 -->
# Crew task pipeline — async-fence batching, conditional-task barrier, and replay-aware start index

**Source:** crewAI MIT `main@9e9a8577`; Codebase Memory `ext-crewAI`. **Question:** How does sequential process execution interleave sync tasks, async task waves, and ConditionalTask skips without breaking context ordering?

## Connected graph-selected seam
**Path/Symbol:** `lib/crewai/src/crewai/crew.py` — `_execute_tasks` (:1558), `_handle_conditional_task` (:1629), `_get_execution_start_index` (:1550), `_prepare_tools` (:1645).
**Signature:** `_execute_tasks(tasks: list[Task], start_index: int | None = 0, was_replayed: bool = False) -> CrewOutput`.
**Data Shape:** `futures: list[tuple[Task, Future[TaskOutput], int]]` accumulates async tasks until a sync task (or end) forces a join — the "async fence"; `last_sync_output` feeds async contexts.

### Decisive source
```python
# :1582 the fence pattern
for task_index, task in enumerate(tasks):
    exec_data, task_outputs, last_sync_output = prepare_task_execution(...)
    if exec_data.should_skip:
        continue
    if isinstance(task, ConditionalTask):
        skipped_task_output = self._handle_conditional_task(
            task, task_outputs, futures, task_index, was_replayed)
        if skipped_task_output:
            task_outputs.append(skipped_task_output)
            continue
    if task.async_execution:
        context = self._get_context(task, [last_sync_output] if last_sync_output else [])
        future = task.execute_async(agent=..., context=context, tools=...)
        futures.append((task, future, task_index))
    else:
        if futures:                                   # SYNC TASK = FENCE
            task_outputs.extend(self._process_async_tasks(futures, was_replayed))
            futures.clear()
        ...task_output = task.execute_sync(...)

# :1550 resume replays from first task with no output
def _get_execution_start_index(self, tasks):
    if self.checkpoint_kickoff_event_id is None:
        return None
    for i, task in enumerate(tasks):
        if task.output is None:
            return i
```

**Flow:** each index → prepare (agent resolution, cache-handler offer, tool merge) → ConditionalTasks drain pending futures FIRST then evaluate condition against completed outputs (skip ⇒ placeholder output keeps indices aligned) → async tasks launch with only-last-sync-output context → sync task joins all futures before executing so its context sees complete outputs in ORDER → final tail join → `_create_crew_output`. Hierarchical mode swaps in a manager agent (`_create_manager_agent` :1518) that gets delegation tools and — if crew cache enabled — the crew's cache handler offered OUTSIDE the agents loop.
**Invariant:** Async tasks must NOT be given full task_outputs contexts (only `last_sync_output`) because their completion order is nondeterministic; the fence guarantees deterministic ordering for everything after it. `_get_execution_start_index` returns None when checkpointing is off — replay awareness is checkpoint-gated, not default.
**Probe:** `grep -c '_process_async_tasks' lib/crewai/src/crewai/crew.py` → `4`; `grep -cF "Manager agent should not have tools" lib/crewai/src/crewai/crew.py` → `2`.
**Direct test:** `tests/test_crew_thread_safety.py` (ThreadPoolExecutor kickoff isolation, suite green); manager-tool guard exercised via hierarchical suites in `tests/test_crew.py`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-crewAI", query: "Crew._execute_tasks executes tasks sequentially returns final output", limit: 5 });
// → ext-crewAI.lib.crewai.src.crewai.crew.Crew._execute_tasks Method 1558-1627
```

## Verdict
Adopt the async-fence batching + conditional-barrier + gated replay-index contract for any ordered agent pipeline with parallel branches. Adapt Task/Agent classes. Omit delegation/code-execution/multimodal tool injection details inside `_prepare_tools` (feature surface).
