<!-- capsule-v2 -->
# Latest-wins ticket threads — how do you cancel an in-flight job when a newer event for the same object arrives?

**Source:** sweep (Apache-2.0) `main@a8b8b67bda4f`; Codebase Memory `sweep`. **Question:** When a second webhook event targets the same issue, what happens to the first running job — queue behind it, run in parallel, or replace it?

## Keyed thread replacement with ctypes async cancellation
**Path/Symbol:** `sweepai/api.py:166-180` (`call_on_ticket`), `sweepai/api.py:141-158` (`terminate_thread`) (line range).
**Signature:** `def call_on_ticket(*args, **kwargs)` / `def terminate_thread(thread: threading.Thread)`.
**Data Shape:** Module-global dict `on_ticket_events: dict[str, Thread]` keyed `f"{repo_full_name}-{issue_number}"`; threads also appended to `global_threads` list (never pruned).

### Decisive source
```python
e = on_ticket_events.get(key, None)
if e:
    logger.info(f"Found previous thread for key {key} and cancelling it")
    terminate_thread(e)

thread = threading.Thread(target=run_on_ticket, args=args, kwargs=kwargs)
on_ticket_events[key] = thread
thread.start()
```
```python
exc = ctypes.py_object(SystemExit)
res = ctypes.pythonapi.PyThreadState_SetAsyncExc(ctypes.c_long(thread.ident), exc)
if res == 0:
    raise ValueError("Invalid thread ID")
elif res != 1:
    # Call with exception set to 0 is needed to cleanup properly.
    ctypes.pythonapi.PyThreadState_SetAsyncExc(thread.ident, 0)
    raise SystemError("PyThreadState_SetAsyncExc failed")
```

**Flow:** new event → lookup live thread by `repo-issue` key → if present, async-inject `SystemExit` into it → spawn replacement thread under the same key. The whole dispatch is wrapped in try/except-log, so a failed kill never blocks the new job.
**Invariant:** At most one ticket job per `(repo, issue)` runs at a time; the newest event always wins. Async exceptions only land *between bytecodes* — a thread blocked inside a C call (network I/O) is not interruptible until it returns to Python; termination is cooperative-by-accident, not guaranteed.
**Probe:** No direct unit test exists for `call_on_ticket`/`terminate_thread` (coverage caveat). Graph probe executed at pin: `trace_path(call_on_ticket, both, depth 2)` → callers exactly `{handle_event, handle_github_webhook(via handle_request), cli.main}`; callees `{dict.get, list.append, terminate_thread}` — no queueing layer between router and thread.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.trace_path({ project: "sweep", function_name: "call_on_ticket", direction: "both", depth: 2 });
```

## Verdict
Adopt the key-registry + kill-then-restart pattern for per-object idempotent jobs and the res==0/res!=1 cleanup ladder if you must use async-exc; adapt to your runtime's structured cancellation (asyncio tasks, futures) where available; omit the unbounded `global_threads` append-only list and the raw-ctypes approach in favor of cooperative cancel flags when jobs hold locks or write files mid-flight.
