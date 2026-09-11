<!-- capsule-v2 -->
# Completion thread pool — queue-coupled workers with request-id correlation

**Source:** graphrag MIT `<branch>@<commit>`; Codebase Memory `graphrag`. **Question:** how does a pipeline drive N concurrent LLM calls from a single-threaded loop without async, and correlate responses back to requests?

## Connected graph-selected seam
**Path/Symbol:** `graphrag_llm/threading/completion_thread.py`: `CompletionThread(threading.Thread)` (:59-91); `threading/completion_thread_runner.py`: `completion_thread_runner` (:143), `_start_completion_thread_pool` (:115), `_process_input` (:207), `_process_output` (:189), `ThreadedLLMCompletionFunction` Protocol (:62); same pattern mirrored in `embedding_thread*.py`.
**Signature:** `CompletionThread(*, quit_process_event, input_queue, output_queue, completion)` — worker pulls `(request_id, args)`, calls the completion function, pushes `(request_id, response_or_exception)`.
**Data Shape:** queues carry `(request_id: str, payload)` tuples; exceptions travel as payloads (never raised in the worker).

### Decisive source
```ts
def run(self):
    while not self._quit_process_event.is_set():
        try: input_data = self._input_queue.get(timeout=1)
        except Empty: continue                      # poll so quit events are noticed
        if input_data is None: break                # sentinel = clean shutdown
        request_id, data = input_data
        try:
            response = self._completion(**data)
            self._output_queue.put((request_id, response))
        except Exception as e:
            self._output_queue.put((request_id, e)) # error IS a result
```

**Flow:** `completion_thread_runner` starts a pool of CompletionThreads sharing one input/output queue pair → the main loop submits `(id, args)` and later matches responses by id → errors are delivered as results so one failure never kills a worker → shutdown via quit event + None sentinel.
**Invariant:** workers hold no shared mutable state (all coupling through queues); every request gets exactly one correlated response (success or exception); polling timeout keeps shutdown responsive.
**Probe:** `tests/` threading tests (N requests round-robin across threads; exception propagated with matching request_id; sentinel stops workers).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "graphrag", query: "CompletionThread completion_thread_runner input_queue output_queue request_id", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt queue-coupled completion workers with request-id correlation and errors-as-results for sync pipelines needing LLM concurrency; adapt pool sizing to quota.
