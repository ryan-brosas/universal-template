<!-- capsule-v2 -->
# Node-level error-handler routing — How can a graph recover from a failed node without treating the error as fatal?

**Source:** LangGraph MIT `main@f09cfe8ffc1eeffd68f4b628ed69c30f7cad229f`; Codebase Memory `ext-langgraph`. **Question:** How does a designated handler node receive another node's failure while the panic path stays quiet about already-handled errors?

## ERROR_SOURCE_NODE marker + handled-exception-id set
**Path/Symbol:** `libs/langgraph/langgraph/pregel/_runner.py:_should_route_to_error_handler` (:171-175), commit marker append (:598-604), tick routing (:283-306 sync, :488-502 async), `_loop.schedule_error_handler` (:589-598) + drain (:751-816).
**Signature:** `node_error_handler_map: Mapping[str, str]` (failed-node → handler-node); `schedule_error_handler(failed_task, error) -> PregelExecutableTask | None`.
**Data Shape:** Marker write tuple: `(task_id, ERROR_SOURCE_NODE, node_name)` — appended by `commit()` ONLY when `_should_route_to_error_handler(task)` (task is mapped AND is not itself the handler). Handler task carries `NodeError` via config (`CONFIG_KEY_NODE_ERROR`) with signature-based injection.

### Decisive source
```python
else:
    # save error to checkpointer
    task.writes.append((ERROR, exception))
    if self._should_route_to_error_handler(task) and not isinstance(
        exception, GraphBubbleUp
    ):
        task.writes.append((ERROR_SOURCE_NODE, task.name))
        self._handled_exception_ids.add(id(exception))
    self.put_writes()(task.id, task.writes)
```
**Flow:** Task fails → runner checks map → schedules handler as a REAL pregel task (participates in triggers/writes/checkpointing; runs via run_with_retry so IT can retry/interrupt) and records `id(exception)` in `_handled_exception_ids`; the failed future goes into SKIP_RERAISE_SET. The stop-condition and `_panic_or_proceed` consult handled-ids so the SAME exception object never re-fataled through the normal path. Durability of the handoff: `put_writes` collects futures carrying ERROR_SOURCE_NODE into `_error_handler_write_futs`, which `schedule_error_handler` drains — the marker write is durable BEFORE the handler starts.

**Invariant:** Handlers never handle themselves (`task.name in self.error_handler_nodes → False`) preventing recursion loops. Routing keys on exception IDENTITY not equality, because equal-but-distinct exceptions from sibling tasks must fail independently. GraphBubbleUp (interrupts/resume machinery) is never routed to handlers. On resume after crash, pending ERROR_SOURCE_NODE writes re-arm handlers via `_resume_error_handlers_if_applicable`.

**Probe:** `grep -n 'ERROR_SOURCE_NODE' libs/langgraph/langgraph/pregel/_runner.py | head -6` → :34/:601(+marker append); `grep -c '_handled_exception_ids' libs/langgraph/langgraph/pregel/_runner.py` → 16. Direct tests: pinned via `tests/test_pregel.py` checkpoint-recovery family at :5372 (`test_checkpoint_recovery` asserts `state.tasks[0].error` content and next==(node1,)).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-langgraph", query: "prepare_node_error_handler_task", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt marker-write + identity-set handling for supervised recovery in step engines. Adapt the map/config plumbing to your DI style. Omit resume re-arm logic only if your host cannot crash between failure and handler execution.
