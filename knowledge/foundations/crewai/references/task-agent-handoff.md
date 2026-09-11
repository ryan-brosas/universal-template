<!-- capsule-v2 -->
# Task→agent handoff — how does a Task drive the executor, collect tool failures, and apply guardrails?

**Source:** crewAI MIT `main@f4731f5025f861c78e3af0487cc80bf5e7c64782`; Codebase Memory `ext-crewAI`. **Question:** What is the exact Task._execute_core sequence from event emission to TaskOutput, and where do hooks/guardrails/failure collection attach?

## Task._execute_core (+ async twin)
**Path/Symbol:** `lib/crewai/src/crewai/task.py:806-930` (`_execute_core`), `:585-593` (`execute_sync`), `:609-638` (`execute_async` daemon-thread + Future), `:650+` (`_aexecute_core`); agent side `agent/core.py:816-956` (`execute_task`, `_execute_with_timeout`).
**Signature:** `def _execute_core(self, agent, context, tools) -> TaskOutput`; `def execute_async(...) -> Future[TaskOutput]`.
**Data Shape:** Produces `TaskOutput(name, description, expected_output, raw, pydantic, json_dict, agent, output_format, messages=agent.last_messages, tool_failures=list(execution_failures))`.

### Decisive source
```python
task_id_token = set_current_task_id(str(self.id))
self._store_input_files()
...
executor = agent.agent_executor
if not (executor and executor._resuming and resume_task_scope(str(self.id))):
    crewai_event_bus.emit(self, TaskStartedEvent(context=context, task=self))

pre_step_ctx = StepContext(kind="task", step_name=..., payload=context)
dispatch(InterceptionPoint.PRE_STEP, pre_step_ctx)
context = pre_step_ctx.payload          # PRE_STEP hooks may REWRITE context

with tool_failure_collector() as execution_failures:   # ContextVar-scoped
    result = agent.execute_task(task=self, context=context, tools=tools)
...
task_output = TaskOutput(..., tool_failures=list(execution_failures))
for idx, guardrail in enumerate(self._guardrails):     # list form
    task_output = self._invoke_guardrail_function(...)
post_step_ctx = StepContext(kind="task", output=task_output, payload=task_output)
dispatch(InterceptionPoint.POST_STEP, post_step_ctx)
task_output = cast(TaskOutput, post_step_ctx.payload)  # POST_STEP may rewrite
```

**Flow:** Set current-task contextvar → store input files → resolve agent (arg > self.agent; raise the no-agent "execute in a Crew" error) → resume-scope check gates duplicate TaskStarted events → PRE_STEP dispatch → run agent under failure collector → `_post_agent_execution` → output typing branch (BaseModel / pydantic / json export) → guardrail loop (each can retry by returning `(valid: False, error)` semantics internally) → POST_STEP dispatch → assign `self.output`, stamp end_time, run `self.callback` (awaited via asyncio.run when it returns a coroutine) → memory write on crew.
**Invariant:** The collector is CONTEXTVAR-scoped so an agent shared across concurrent tasks reports only THIS execution's failures into its own TaskOutput. Agent-side timeout wraps the WHOLE execute in a ThreadPoolExecutor future with `contextvars.copy_context()`; `concurrent.futures.TimeoutError` becomes a friendly TimeoutError while deliberate-stop exceptions are re-raised unwrapped ("Wrapping a deliberate stop in RuntimeError would hide it … and trigger the retry loop instead"); sync invoke inside a running loop closes the returned coroutine and raises with guidance to use kickoff_async.
**Probe:** `tests/test_crew.py::test_tool_failure_collector*` family and task tests under `tests/task/`; timeout anchors grep `grep -n '_passthrough_exceptions' lib/crewai/src/crewai/agent/core.py` → import + use at `:919-923`.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-crewAI", query: "Task execute_core guardrail tool_failure_collector", limit: 6, detail: "ids" });
```

## Verdict
Adopt the PRE/POST_STEP rewrite points plus scoped failure collection; adapt StepContext fields to your hook system; omit the legacy single `_guardrail` field (list form supersedes it at this pin).
