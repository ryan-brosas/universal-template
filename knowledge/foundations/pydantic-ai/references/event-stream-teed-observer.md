<!-- capsule-v2 -->
# Teed event-stream observer vs stream-replacing processor — how do you forward the agent event stream to a handler without breaking memoized node streams consumed from other tasks?

## Source / Question
`pydantic_ai_slim/pydantic_ai/capabilities/process_event_stream.py` @ `main@b3cdbc96` (MIT); Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai`. **Question:** When a capability must observe (or reshape) the run's single event stream, how do you support both an async-handler observer form and an async-generator processor form without dying on anyio's "cancel scope in a different task" error when the wrapped node stream is legitimately resumed in another task? A porter will hold an anyio task group open across `yield`s and corrupt every abandoned-stream path.

## Path / Symbol
`capabilities/process_event_stream.py` — `ProcessEventStream` dataclass (:24–88), `wrap_run_event_stream` (:90–182): handler probe (:99–103), probe-close-and-reinvoke (:107–116), plain-task rationale comment (:118–131), pump loop (:132–170), BaseException teardown (:171–179), terminal `await handler_task` (:182), `get_serialization_name() → None` (:184–186).

## Signature
```python
async def wrap_run_event_stream(self, ctx: RunContext[AgentDepsT], *,
                                stream: AsyncIterable[AgentStreamEvent]) -> AsyncIterable[AgentStreamEvent]
```
Handler union: `EventStreamHandlerFunc` (async def → None) | `EventStreamProcessorFunc` (async generator yielding events).

## Data Shape
Form discrimination is by RETURN TYPE of `self.handler(ctx, stream)` — an `AsyncIterator` means processor; anything else is an un-awaited coroutine (observer). Introspecting the return beats `inspect.isasyncgenfunction` because it also works for callable instances (:96–98). The observer gets a fresh `anyio.create_memory_object_stream()` pair per run; events are ALSO always yielded downstream unchanged (teed view).

### Decisive source
The task-affinity invariant (:118–131):
```python
# The handler runs in a plain `asyncio` task rather than an `anyio` task group held open
# across the `yield`s below. A task group is bound to the task that entered it ... the node
# stream it wraps is memoized, so it can legitimately be resumed elsewhere ... Exiting the
# group from a different task raises anyio's "cancel scope in a different task" error,
# replacing whatever the caller was actually doing. A task has no such affinity.
```

**Flow:** (1) Probe handler once per stream; if processor, yield its events verbatim (it REPLACES the stream globally — dropping a `FinalResultEvent` makes `run_stream()` wait for the whole response; output content is unaffected because `ModelResponse` accumulates from the RAW model stream before processors see events). (2) Observer: close the probe coroutine (nothing ran), re-invoke with a teed receive stream inside `asyncio.create_task(run_handler())`. (3) Pump loop: create `pull_next()` task per iteration; while handler_alive race `(next_task, handler_task)` FIRST_COMPLETED; handler exiting cleanly ⇒ stop sending but keep forwarding downstream. (4) Handler raised/cancelled ⇒ cancel+drain the in-flight pull, `aclose_if_supported(stream_iterator)`, re-await handler_task, propagate. (5) `send()` raising Broken/ClosedResourceError (handler bailed early) just flips `handler_alive=False`. (6) Any BaseException from consumer/source ⇒ cancel_and_drain(handler_task, next_task?) + close source iterator + re-raise — being cancelled while awaiting a task does NOT cancel it, so without this the parked pull advances the source one step past exit and may sit inside `anext()` when someone else closes the iterator. (7) After the loop, close send_stream then `await handler_task` to surface handler exceptions.

**Invariant:** Nothing upstream may hold an anyio cancel scope/task group open across a yield of the wrapped stream (each pull resumes in a fresh task). Registration auto-enables streaming so handlers fire even under `agent.run()`; durable-execution replay runs the handler in workflow code and requires determinism.

**Probe:** `tests/test_capability_process_event_stream.py` — `test_observer_bailout_does_not_break_downstream` (:189), `test_abandoned_model_request_stream_tears_down_the_handler` (:244), `test_abandoned_call_tools_stream_tears_down_the_handler` (:323), `test_cancelled_consumer_closes_stalled_source` (:544), `test_streamed_result_can_be_consumed_in_another_task` (:771), `test_processor_shapes_streamed_text_but_not_the_output` (:797), `test_handler_fires_under_every_drive_mode` (:669).

## Get live surrounding code
**Retrieve:**
```
search_graph --project mnt-hdd-utopia-inspo-pydantic-ai --query 'ProcessEventStream wrap_run_event_stream memory object stream'
```

## Verdict
**Adopt** the dual-form probe, the plain-asyncio-task (never cross-yield task group) rule, the race-with-clean-exit-flips-alive pump, and the cancel-and-drain teardown ordering. **Adopt** the global-vs-private-view distinction: observers teed, processors replace the stream for everyone including `FinalResultEvent` consumers. **Omit** the realtime-session wording if your host has no realtime plane (the wrapping mechanics are identical).
