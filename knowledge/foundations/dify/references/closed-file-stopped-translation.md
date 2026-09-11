<!-- capsule-v2 -->
# closed-file-stopped-translation — How does a client disconnect become a clean cancellation?

**Source:** dify Apache-2.0 `main@8bdf702f`; Codebase Memory `ext-dify`. **Question:** What converts the low-level "I/O on a closed file" error into domain-level "task stopped"?

## Exact-string ValueError match translated to GenerateTaskStoppedError
**Path/Symbol:** `api/core/app/apps/workflow/app_generator.py:WorkflowAppGenerator._handle_response` (:707-749), translation at :742-744; exception class `api/core/app/apps/exc.py` (2L).
**Signature:** `_handle_response(...) -> WorkflowAppBlockingResponse | WorkflowAppPausedBlockingResponse | Generator[WorkflowAppStreamResponse, None, None]`.
**Data Shape:** Catches ValueError from the pipeline's stream consumption; matches `e.args[0] == "I/O operation on closed file."` exactly; everything else re-raised after logging.

### Decisive source
```python
def _handle_response(self, application_generate_entity, workflow, queue_manager, user,
                     draft_var_saver_factory, stream=False):
    # init generate task pipeline
    generate_task_pipeline = WorkflowAppGenerateTaskPipeline(...)
    try:
        return generate_task_pipeline.process()
    except ValueError as e:
        if len(e.args) > 0 and e.args[0] == "I/O operation on closed file.":  # ignore this error
            raise GenerateTaskStoppedError()
        else:
            logger.exception("Fails to process generate task pipeline, task_id: %s",
                             application_generate_entity.task_id)
            raise e
```

**Flow:** client disconnects mid-SSE → generator's writes hit a closed socket/file → Python's buffered writer raises `ValueError("I/O operation on closed file.")` → this handler recognizes the exact message and re-raises as GenerateTaskStoppedError → the worker thread's taxonomy swallows it silently (cancelled, not crashed).
**Invariant:** Only the EXACT first arg translates — any other ValueError is a real bug and must log + propagate; the translation sits at the response boundary so both blocking and streaming paths share it; upstream tracks this string-matching as fragile debt but it remains the contract between wsgi layer and app layer.
**Probe:** `grep -cF 'on closed file.' core/app/apps/workflow/app_generator.py` → 1; direct test `tests/unit_tests/core/app/apps/workflow/test_app_generator_extra.py::test_handle_response_closed_file_raises_stopped` (same assertion triple exists for advanced_chat and message-based twins — behavior shared across all three generators).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-dify", query: "_handle_response pipeline process ValueError closed file", limit: 10 });
```

## Verdict
Adopt boundary translation of transport-layer breakage into one domain cancellation error. Adapt the matched signature to your server stack (this string is cpython-wsgiref flavored). Omit nothing else in the handler.
