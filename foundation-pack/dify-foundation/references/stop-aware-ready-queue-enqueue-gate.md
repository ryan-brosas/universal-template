<!-- capsule-v2 -->
# stop-aware-ready-queue-enqueue-gate — How does a stopped run prevent the NEXT node from starting without killing the in-flight node?

**Source:** dify Apache-2.0 `main@44aec257`; Codebase Memory `ext-dify`. **Question:** After a user stop lands mid-node, what keeps queued successors from executing while letting the running node finish? (Fix #41090: previously stops were honored only at stream boundaries between nodes, so non-streaming runs kept scheduling.)

## ReadyQueue decorator rejecting writes once abort signals arm
**Path/Symbol:** `api/core/app/apps/workflow/stop_aware_ready_queue.py:StopAwareReadyQueue` (:12-56) + `attach_stop_aware_ready_queue` (:58-68); wired in `api/core/app/apps/workflow/app_runner.py:run` (:164) and `api/core/app/apps/advanced_chat/app_runner.py` (:234).
**Signature:** `StopAwareReadyQueue(inner: ReadyQueue, *, task_id: str, graph_execution: GraphExecutionProtocol)`; `attach_stop_aware_ready_queue(graph_runtime_state: GraphRuntimeState, *, task_id: str) -> None`.
**Data Shape:** Decorator over the graphon `ReadyQueue` installed by mutating `graph_runtime_state._ready_queue`. Rejection predicate = `graph_execution.aborted OR is_app_task_stop_flag_set(task_id)` — BOTH the engine-local abort state AND the legacy Redis stop flag (`generate_task_stopped:{task_id}`, 600s TTL). Attach is idempotent: an existing `StopAwareReadyQueue` is never double-wrapped (`isinstance(current, StopAwareReadyQueue): return`, test-pinned identity).

### Decisive source
```python
def _should_reject(self) -> bool:
    return self._graph_execution.aborted or is_app_task_stop_flag_set(self._task_id)

def put(self, item: ReadyTask) -> None:
    if self._should_reject():
        return                      # silently drop; engine treats enqueue as fire-and-forget
    self._inner.put(item)

def attach_stop_aware_ready_queue(graph_runtime_state, *, task_id) -> None:
    current = graph_runtime_state.ready_queue
    if isinstance(current, StopAwareReadyQueue):
        return
    graph_runtime_state._ready_queue = StopAwareReadyQueue(
        current, task_id=task_id, graph_execution=graph_runtime_state.graph_execution,
    )
```

**Flow:** stop arrives (channel emits `AbortCommand`) → engine marks run aborted / coordinator sets Redis flag → GraphEngine drain STILL enqueues successor tasks after the abort → every `put()` consults the predicate → rejected puts vanish silently → the in-flight node completes naturally → `get()` keeps draining the wrapped queue so nothing deadlocks.
**Invariant:** REJECT WRITES, NEVER READS — `get`/`task_done`/`qsize`/`drain`/`dumps`/`loads` all delegate unchanged (test-pinned one-by-one); rejection is a SILENT DROP, never an exception, because the scheduler has no error path for refused successors; the gate reads two independent signals (engine flag + Redis flag) so either producer alone stops scheduling; idempotent attach makes the resume path safe to call twice.
**Probe:** `cd api && .venv/bin/pytest -p no:cacheprovider -o addopts= tests/unit_tests/core/app/apps/workflow/test_stop_aware_ready_queue.py -q` → 5 passed (accept-while-active, reject-on-aborted, reject-on-flag, wrap-once identity, full read-delegation). EXECUTED GREEN at `44aec257` via repo venv.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-dify", query: "StopAwareReadyQueue attach_stop_aware_ready_queue ready queue", limit: 10 });
```

## Verdict
Adopt the write-gate/decorator shape for any cooperative scheduler shutdown (drop future work, never cancel in-flight units, keep consumer semantics identical). Adapt the signal sources (any shared "stop requested" latch works; Dify uses engine state + a Redis TTL flag). Omit the private-attribute install (`_ready_queue`) if your runtime exposes a proper setter. Direct tests cover all five behaviors at the pin; no coverage caveat.
