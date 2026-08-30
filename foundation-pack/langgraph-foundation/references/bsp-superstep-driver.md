<!-- capsule-v2 -->
# BSP superstep driver — How does the sync driver loop execute a superstep and emit output without deadlocking?

**Source:** LangGraph MIT `main@f09cfe8ffc1eeffd68f4b628ed69c30f7cad229f`; Codebase Memory `ext-langgraph`. **Question:** How do tick, runner, and stream interleave so channel updates from step N only become visible in step N+1?

## Bulk Synchronous Parallel loop with a single live waiter
**Path/Symbol:** `libs/langgraph/langgraph/pregel/main.py:Pregel.stream` (:2655-3023, driver `while loop.tick()` at :2964).
**Signature:** `stream(input, config=None, *, stream_mode=None, output_keys=None, interrupt_before=None, interrupt_after=None, durability=None, control=None, subgraphs=False, version='v1') -> Iterator`.
**Data Shape:** SyncQueue (deque + Semaphore(0)) carries `(ns, mode, payload)` tuples; PregelRunner gets `submit=WeakMethod(loop.submit)`, `put_writes=WeakMethod(loop.put_writes)`; `get_waiter` memoizes ONE `loop.submit(stream.wait)` future.

### Decisive source
```python
# Similarly to Bulk Synchronous Parallel / Pregel model
# computation proceeds in steps, while there are channel updates.
# Channel updates from step N are only visible in step N+1
# channels are guaranteed to be immutable for the duration of the step,
# with channel updates applied only at the transition between steps.
while loop.tick():
    for task in loop.match_cached_writes():
        loop.output_writes(task.id, task.writes, cached=True)
    for _ in runner.tick(
        [t for t in loop.tasks.values() if not t.writes],
        timeout=self.step_timeout,
        get_waiter=get_waiter,
        schedule_task=loop.accept_push,
    ):
        # emit output
        yield from _output(...)
    loop.after_tick()
```
**Flow:** `_defaults()` resolves modes/checkpointer/durability → `SyncPregelLoop.__enter__` loads checkpoint + applies input writes → per iteration: `tick()` prepares tasks (returns False on done/out_of_steps/draining/interrupt) → cached-write replay → `runner.tick()` executes tasks concurrently, yielding as futures complete → `_output` drains the stream queue → `after_tick()` applies writes + checkpoints → after the loop: recursion-limit check raises `GraphRecursionError`, draining status raises `GraphDrained`.

**Invariant:** Channels are read-only during task execution; ALL writes (including PUSH tasks accepted mid-step via `accept_push`) are applied only in `after_tick()`. The eager-waiter path must keep exactly one `stream.wait` future alive ("we are careful to have a single waiter live at any one time because on exit we increment semaphore count by exactly 1") — exit releases the semaphore instead of cancelling, since sync futures cannot be cancelled. When no checkpointer exists, `durability` warns it has no effect. A v1 stream strips inherited `StreamMessagesHandlerV2` handlers but keeps v1 handlers so outer/inner message streams compose.

**Probe:** `grep -n 'while loop.tick()' libs/langgraph/langgraph/pregel/main.py` → exactly 2 hits (:2964 sync, :3437 async); `grep -n 'GraphRecursionError\|GraphDrained' libs/langgraph/langgraph/pregel/main.py | head -4` → :3011/:3015/:3492/:3496. Direct tests: `tests/test_pregel.py:767 test_invoke_two_processes_two_in_two_out_invalid` (LastValue + 2 writers ⇒ InvalidUpdateError), `:5334 test_concurrent_execution_thread_safety` (10 threads × independent invokes).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-langgraph", query: "PregelRunner tick commit", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the BSP discipline (immutable-in-step reads, apply-at-transition, deterministic exit ladder) for any concurrent step engine. Adapt the stream-mode payload shapes and langchain callback wiring to your host. Omit the deprecated `checkpoint_during`→`durability` shim and v1/v2 overload surface.
