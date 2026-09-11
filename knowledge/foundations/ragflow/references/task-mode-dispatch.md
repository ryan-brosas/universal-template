<!-- capsule-v2 -->
# task-mode-dispatch — how does one Redis consumer serve parse, graphrag, raptor, dataflow, memory?

**Source:** ragflow Apache-2.0 `main@9ea83b7a9d003d948fe4c99c6f35de02115a96e8`; Codebase Memory `ext-ragflow`. **Question:** What is the dispatch order in do_handle_task and which branches return early?

## Task-type dispatch ladder
**Path/Symbol:** `do_handle_task` `rag/svr/task_executor.py:1408-1597`; run-mode selector `handle_task` `:1745-1775`; unacked-drain collect `:220-291`.
**Signature:** `do_handle_task(task)` (task dict from `TaskService.get_task(msg["id"])`); `TE_RUN_MODE` env ∈ {"0" refactored, "1" dry-run compare, else original}.
**Data Shape:** special doc ids `CANVAS_DEBUG_DOC_ID` / `GRAPH_RAPTOR_FAKE_DOC_ID` mark canvas + KB-fanout tasks; fanout doc list rides `task["doc_ids"]` on the MESSAGE, mirrored onto the DB row (`collect :274-280`).

### Decisive source
```python
if task_type == "memory":  ...return
if task_type == "dataflow" and task.get("doc_id","") == CANVAS_DEBUG_DOC_ID:
    await run_dataflow(task); return
...
if task_type[: len("dataflow")] == "dataflow":
    await run_dataflow(task); return
if task_type == "raptor":   # KB-scoped summarization tree
    ...
elif task_type == "graphrag":  ... progress_callback(prog=1.0,...); return
elif task_type == "mindmap": progress_callback(1, "place holder"); return
elif task_type == "skill":  progress_callback(-1, "Skill generation requires the refactored task executor (TE_RUN_MODE=0)."); return
else:  # Standard chunking methods → build_chunks → embedding → insert
```

**Flow:** handle_task pulls from Redis stream via UNACKED_ITERATOR (drains pending/unacked FIRST — crash recovery without re-enqueue), then queue_consumer → deep-copy into CURRENT_TASKS → mode switch (refactored/dry-run/original) → do_handle_task dispatch above → finally records PipelineOperationLog (skipped for dataflow) → unconditional terminal `redis_msg.ack()` at :1810. Raptor/graphrag both lazily self-heal missing parser_config blocks by writing full default configs back to the KB row before running; both serialize through `async with kg_limiter`.
**Invariant:** embedding model bind happens ONCE before dispatch (`vts,_ = encode(["ok"])` fixes vector_size used by init_kb); a failed bind fails the whole task with progress -1. The ack is last — any exception path still lands it exactly once.
**Probe:** `grep -n 'def do_handle_task\|def handle_task\|def collect' rag/svr/task_executor.py` → :1408/:1745/:220; `sed -n '1757,1762p' rag/svr/task_executor.py | grep -c 'run_mode == .1.'` → 1; `grep -n 'kg_limiter' rag/svr/task_executor.py | head -2` → import + `async with kg_limiter:` :1501/:1561. Executed GREEN at pin.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ragflow", query: "do_handle_task task_type raptor graphrag dispatch", limit: 5, fields: ["name", "file"] });
```

## Verdict
Adopt the ordered early-return ladder + drain-then-consume loop + single-ack discipline; adapt TE_RUN_MODE-style mode switching if you have no dry-run twin; omit RecordingContext plumbing (test-compare product feature).
