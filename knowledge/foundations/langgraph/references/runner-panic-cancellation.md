<!-- capsule-v2 -->
# Runner panic & sibling cancellation — When one task fails, what exactly happens to its peers and their writes?

**Source:** LangGraph MIT `main@f09cfe8ffc1eeffd68f4b628ed69c30f7cad229f`; Codebase Memory `ext-langgraph`. **Question:** How does the executor guarantee fail-fast cancellation while still committing every finished task's writes?

## FuturesDict stop-condition + _panic_or_proceed; interrupts are NOT failures
**Path/Symbol:** `libs/langgraph/langgraph/pregel/_runner.py:FuturesDict` (:75-133), `PregelRunner.tick` (:176-358), `_should_stop_others` (:616-634), `_panic_or_proceed` (:646-712), `commit` (:574-613).
**Signature:** `tick(tasks, *, reraise=True, timeout=None, retry_policy=None, get_waiter=None, schedule_task) -> Iterator[None]` — a GENERATOR: yields before scheduling (caller gives control back), once per completed batch, and after the final wait.
**Data Shape:** FuturesDict maps future → task|None (None = stream waiter); tracks `counter`, `done` set, threading/asyncio Event; `should_stop` injected by the runner so handled exceptions don't trip it.

### Decisive source
```python
def on_done(self, task, fut):
    try:
        if cb := self.callback():   # -> runner.commit(task, exception)
            cb(task, _exception(fut))
    finally:
        with self.lock:
            self.done.add(fut); self.counter -= 1
            if self.counter == 0 or self.should_stop(self.done):
                self.event.set()    # wake the waiter early on fatal error
...
# _panic_or_proceed: for each done future with an exception that is not
# GraphBubbleUp / already-handled / in SKIP_RERAISE_SET:
#   cancel ALL inflight futures, then raise.
# GraphInterrupts are COLLECTED across futures and re-raised combined:
if interrupts:
    raise GraphInterrupt(tuple(i for exc in interrupts for i in exc.args[0]))
if inflight:  # got here means we timed out
    while inflight: inflight.pop().cancel()
    raise timeout_exc_cls("Timed out")
```
**Flow:** Each task runs via run_with_retry on the loop's executor; completion callback commits writes IMMEDIATELY (success → put_writes with NO_WRITES marker if empty; failure → `(ERROR, exc)` write first). A fatal exception flips `should_stop(done)` so the event wakes without waiting for stragglers; tick exits its wait loop, then panic cancels inflight tasks and re-raises (traceback frames from EXCLUDED_FRAME_FNAMES stripped recursively from the tail). Cancelled siblings get their CancelledError committed as ERROR writes too — so the superstep can finish coherently.

**Invariant:** Interrupts never trigger cancellation of peers (`GraphBubbleUp` exempted in both `_should_stop_others` and panic); multiple parallel interrupts merge into one GraphInterrupt carrying every payload. Single-task fast path exists but MUST fall through to the general schedule path when the failed task spawned an error-handler task. Commit-before-panic ordering means no completed work is lost when the step aborts.

**Probe:** `grep -n 'SKIP_RERAISE_SET' libs/langgraph/langgraph/pregel/_runner.py | wc -l` → 8 sites; `grep -n '_handled_exception_ids' libs/langgraph/langgraph/pregel/_runner.py | wc -l` → 16. Direct tests: `tests/test_pregel.py:1173 test_concurrent_emit_sends`, `:5334 test_concurrent_execution_thread_safety`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-langgraph", query: "PregelRunner commit", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt commit-immediately-then-panic semantics with interrupt-exempt fail-fast — portable to any future-based executor. Adapt the generator-yield protocol to your host's streaming model. Omit traceback-frame stripping unless you also own the frames being hidden.
