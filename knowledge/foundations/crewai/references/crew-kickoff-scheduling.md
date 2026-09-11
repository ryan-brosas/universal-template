<!-- capsule-v2 -->
# Crew kickoff + task scheduling — how does the crew-level engine order tasks, fan out async ones, and clean up?

**Source:** crewAI MIT `main@f4731f5025f861c78e3af0487cc80bf5e7c64782`; Codebase Memory `ext-crewAI`. **Question:** What is the exact sequential/hierarchical task execution loop, the async-futures flush rule, and the kickoff teardown contract?

## Crew.kickoff / _execute_tasks
**Path/Symbol:** `lib/crewai/src/crewai/crew.py:992-1086` (`kickoff`), `:1558-1627` (`_execute_tasks`), `:1127+` (`kickoff_async`), `:1332+` (`_arun_*`).
**Signature:** `def kickoff(self, inputs=None, input_files=None, from_checkpoint=None) -> CrewOutput | CrewStreamingOutput`; `def _execute_tasks(self, tasks, start_index=0, was_replayed=False) -> CrewOutput`.
**Data Shape:** Per task: `prepare_task_execution(crew, task, index, start_index, outputs, last_sync)` → `exec_data` (agent/tools/skip decision); async tasks yield `(task, Future[TaskOutput], index)` tuples accumulated in `futures`.

### Decisive source
```python
for task_index, task in enumerate(tasks):
    exec_data, ... = prepare_task_execution(...)
    if exec_data.should_skip: continue
    if isinstance(task, ConditionalTask):
        skipped = self._handle_conditional_task(...)   # flushes futures FIRST
        ...
    if task.async_execution:
        future = task.execute_async(agent=..., context=context, tools=...)
        futures.append((task, future, task_index))
    else:
        if futures:
            task_outputs.extend(self._process_async_tasks(futures, was_replayed))
            futures.clear()
        context = self._get_context(task, task_outputs)   # sync barrier sees ALL
        task_output = task.execute_sync(...)
        self._store_execution_log(task, task_output, task_index, was_replayed)
if futures:
    task_outputs.extend(self._process_async_tasks(futures, was_replayed))
return self._create_crew_output(task_outputs)
```

**Flow:** kickoff: checkpoint restore short-circuit → streaming branch (background thread runs a non-streaming recursive kickoff; chunks via generator; `self.stream` toggled False/True around it) → observability baggage (`set_baggage("crew_context", …)` + OTEL attach) → `begin_execution()` token → event-bus runtime scope → `prepare_kickoff` (input interpolation/validation) → process dispatch (sequential vs hierarchical with manager agent) → after_kickoff callbacks → `_post_kickoff` → usage metrics. Teardown in `finally`: `_drain_memory_writes()` ("Safety net for the exception path; the success path already drained in _create_crew_output"), `clear_files(self.id)` (multimodal temp store), detach baggage/token, end_execution, exit runtime scope. Failure emits `CrewKickoffFailedEvent` then re-raises.
**Invariant:** Async tasks are fire-and-collect BETWEEN sync barriers: any sync task (or conditional task, or end-of-list) first DRAINS all pending futures so context assembly for the next sync task observes every prior output in task order. Task.async threads are daemon threads started with `contextvars.copy_context().run` — contextvars propagate, exceptions land on the Future.
**Probe:** `tests/test_crew.py::test_crew_creation etc.` (crew-level), async ordering pinned by `validate_end_with_at_most_one_async_task` + `validate_async_task_cannot_include_sequential_async_tasks_in_context` validators at `crew.py:780-881`; teardown anchors grep: `grep -n '_drain_memory_writes\|clear_files' lib/crewai/src/crewai/crew.py`.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-crewAI", query: "Crew kickoff execute_tasks futures", limit: 6, detail: "ids" });
```

## Verdict
Adopt the futures-flush-before-sync-barrier pattern and total teardown-in-finally; adapt Process.hierarchical manager wiring separately (delegation tools live in `_prepare_tools`); omit the streaming re-entrancy trick if your host streams natively.
