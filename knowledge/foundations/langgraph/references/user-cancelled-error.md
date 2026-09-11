<!-- capsule-v2 -->
# User-raised CancelledError conversion — How do you tell a node's own CancelledError from framework cancellation?

**Source:** LangGraph MIT `main@f09cfe8ffc1eeffd68f4b628ed69c30f7cad229f`; Codebase Memory `ext-langgraph`. **Question:** A node body raises asyncio.CancelledError — why does that become NodeCancelledError instead of a silent teardown?

## Task.cancelling()==0 ⇒ the raise came from user code
**Path/Symbol:** `libs/langgraph/langgraph/pregel/_retry.py:_is_user_raised_cancelled` (:315-335), async arm (:780-798), `_drain_cancelled` (:337-341).
**Signature:** `_is_user_raised_cancelled() -> bool`; guard: `SUPPORTS_TASK_CANCELLING = sys.version_info >= (3, 11)`.
**Data Shape:** `asyncio.Task.cancelling()` counts PENDING external cancel requests; pregel cancels siblings via `task.cancel()` BEFORE the CancelledError fires, so framework-cancelled tasks observe `cancelling() >= 1`.

### Decisive source
```python
# ``asyncio.Task.cancelling()`` was added in Python 3.11. It reports the number of
# pending cancel requests on the task: ``0`` means no external code asked us to
# cancel — so a ``CancelledError`` observed here was raised by the task body
# itself (the user's node) rather than by pregel cancelling sibling tasks.
...
except asyncio.CancelledError as exc:
    #   1. Pregel cancelled this task because a sibling failed ... let cancellation
    #      propagate so the watchdog/cleanup code in the runner sees a cancelled future.
    #   2. The node body itself raised asyncio.CancelledError (cancelling() == 0).
    #      The runner would otherwise treat this as silent tear-down and the run
    #      would report success even though the node failed (LSD-1507). Convert it
    #      into :class:`NodeCancelledError` ...
    if _is_user_raised_cancelled():
        _finish_timed_attempt(config, attempt_ctx, exc)
        raise NodeCancelledError(task.name) from exc
    _finish_timed_attempt(config, attempt_ctx, exc)
    raise
```
**Flow:** CancelledError arrives → classify via cancelling(): >0 = framework cancel → re-raise untouched (runner commits `(ERROR, CancelledError)` writes and panics); ==0 = user raise → wrap as `NodeCancelledError(task.name)` chained `from exc`, which flows through the ordinary failure path (error writes, retry-policy evaluation, panic). The sync path has NO asyncio context at all — any CancelledError reaching sync run_with_retry is by construction user-raised and converts unconditionally. Unknown contexts return False fail-safe (framework semantics preserved).

**Invariant:** Never swallow CancelledError in engine code — either re-raise or convert-and-chain; swallowing turns failures into phantom successes. The conversion must happen OUTSIDE retry classification so converted errors are retry-eligible like any other Exception.

**Probe:** `grep -n 'cancelling() == 0' libs/langgraph/langgraph/pregel/_retry.py` → 2 hits (:321 comment, :334 code); `grep -c 'cancelling()' libs/langgraph/langgraph/pregel/_retry.py` → 7. Direct tests: `tests/test_retry.py:720 test_run_with_retry_rejects_sync_timeout_without_starting_proc` family pins sync/async divergence around cancellation paths.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-langgraph", query: "_drain_cancelled", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the cancelling()-probe discriminator on any 3.11+ host that runs user coroutines inside cancellable tasks. Adapt the wrapper exception type to your error taxonomy. On <3.11 hosts, accept the documented limitation (return False) rather than heuristics.
