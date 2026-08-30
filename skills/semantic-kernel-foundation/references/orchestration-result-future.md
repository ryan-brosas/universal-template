<!-- capsule-v2 -->
# Orchestration result future — turning a pub-sub actor run into an awaitable, cancellable handle

**Source:** Microsoft semantic-kernel MIT `main@b39d95a34435f4c1d55dd00c86120ce118d847e1`; Codebase Memory `semantic-kernel`. **Question:** How does an orchestration expose a non-blocking invoke whose actor-driven result, exceptions, and cancellation all converge on one awaitable handle?

## OrchestrationResult + OrchestrationBase.invoke
**Path/Symbol:** `python/semantic_kernel/agents/orchestration/orchestration_base.py:OrchestrationResult` (lines 42–88), `OrchestrationBase.__init__` (90–129), `_set_types` (131–160), `invoke` (162–238), default transforms (276–344).
**Signature:** `async def invoke(self, task: str | DefaultTypeAlias | TIn, runtime: CoreRuntime) -> OrchestrationResult[TOut]`; `async def get(self, timeout: float | None = None) -> TOut`; `def cancel(self) -> None`.
**Data Shape:** `OrchestrationResult` holds `background_task: asyncio.Task | None`, `value: TOut | None`, `exception: BaseException | None`, `event: asyncio.Event`, `cancellation_token: CancellationToken`. `DefaultTypeAlias = ChatMessageContent | list[ChatMessageContent]`; `TIn`/`TOut` default to it.

### Decisive source
```python
async def get(self, timeout: float | None = None) -> TOut:
    if timeout is not None:
        await asyncio.wait_for(self.event.wait(), timeout=timeout)
    else:
        await self.event.wait()
    if self.value is None:
        if self.cancellation_token.is_cancelled():
            raise RuntimeError("The invocation was canceled before it could complete.")
        if self.exception is not None:
            raise self.exception
        raise RuntimeError("The invocation did not produce a result.")
    return self.value

def cancel(self) -> None:
    if self.cancellation_token.is_cancelled():
        raise RuntimeError("The invocation has already been canceled.")
    if self.event.is_set():
        raise RuntimeError("The invocation has already been completed.")
    self.cancellation_token.cancel()
    self.event.set()

async def invoke(self, task, runtime) -> OrchestrationResult[TOut]:
    self._set_types()
    orchestration_result = OrchestrationResult[self.t_out]()
    async def result_callback(result: DefaultTypeAlias) -> None:
        transformed_result = await self._output_transform(result) if inspect.iscoroutinefunction(...) \
            else self._output_transform(result)
        orchestration_result.value = transformed_result
        orchestration_result.event.set()
    def inner_exception_callback(exception: BaseException) -> None:
        orchestration_result.exception = exception
        orchestration_result.event.set()
    internal_topic_type = uuid.uuid4().hex          # isolates this run from others
    await self._prepare(runtime, internal_topic_type=internal_topic_type,
                        result_callback=result_callback, exception_callback=inner_exception_callback)
    ...  # str -> USER ChatMessageContent; custom TIn -> input_transform
    background_task = asyncio.create_task(self._start(prepared_task, runtime, internal_topic_type,
                                                      orchestration_result.cancellation_token))
    def outer_exception_callback(task: asyncio.Task) -> None:
        try:
            task.result()
        except BaseException as e:
            orchestration_result.exception = e
            orchestration_result.event.set()
    background_task.add_done_callback(outer_exception_callback)
    orchestration_result.background_task = background_task
    return orchestration_result
```

**Flow:** `invoke` resolves the generic types (`__orig_class__.__args__`, falling back to
`__orig_bases__` TypeVar defaults; anything unresolved raises `TypeError`), builds the result
future, registers actors via the abstract `_prepare` with the two callbacks, normalizes the task
(str → USER ChatMessageContent; already-DefaultTypeAlias passes through; custom TIn goes through
`input_transform`), and starts the abstract `_start` as a background task. Three independent
paths converge on `event.set()`: the result callback (after `output_transform`), the actor-level
exception callback, and the background-task done-callback (catches exceptions raised outside the
runtime). `get(timeout)` waits on the event, then resolves in priority order: value → return;
no value + cancelled → RuntimeError; no value + exception → re-raise it; else "did not produce a
result". `cancel()` is guarded on both sides (already-cancelled and already-completed raise) and
completes by setting the token AND the event, so a blocked `get` wakes into the cancelled branch.
**Invariant:** `invoke` never blocks and never raises for actor failures — every failure mode is
deferred into the handle and surfaces only at `get()`. The uuid4 `internal_topic_type` isolates
concurrent orchestrations sharing one runtime. Cancellation is cooperative: actors already
processing messages finish, but no new messages are processed.
**Probe:** `python/tests/unit/agents/orchestration/test_orchestration_base.py::test_invoke_with_timeout_error` (line 372 — TimeoutError from get), `test_invoke_cancel_before_completion` (388 — "canceled before it could complete"), `test_invoke_with_double_cancel` (407 — "already been canceled"), `test_orchestration_set_types` (115), `test_default_output_transform_custom_type` (317).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "semantic-kernel", query: "OrchestrationBase invoke OrchestrationResult result_callback internal_topic_type _set_types", limit: 10, fields: ["signature", "name", "file"] });
```
(Not executable this pass — MCP surface absent; query kept byte-for-byte for the next connected pass.)

## Verdict
Adopt: the future-handle shape (event + value + exception + cancellation token, three-way
event.set convergence, priority-ordered get() resolution) for any actor/pub-sub orchestration
that must look like a plain awaitable to callers. Adapt the type-resolution mechanics to your
host's generics story. Omit the `__orig_bases__` default fallback if your port requires explicit
type parameters.
