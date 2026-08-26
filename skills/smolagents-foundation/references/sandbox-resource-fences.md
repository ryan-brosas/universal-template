<!-- capsule-v2 -->
# AST interpreter resource fences — what bounds runaway generated code without killing the host?

**Source:** smolagents Apache-2.0 `main@30bb1161`; Codebase Memory `ext-smolagents`. **Question:** How do operation counting, loop caps, wall-clock timeout, and print-output truncation compose so a `while True` in model output cannot hang or flood the agent process?

## Four independent budgets
**Path/Symbol:** `src/smolagents/local_python_executor.py` — constants (:57-60), per-node counter inside `evaluate_ast` (:1444-1448), `MAX_WHILE_ITERATIONS` check (:447-458), `timeout` decorator (:285-320), applied at :1664-1665; `PrintContainer` (:240-263) + truncation (:1644-1652); `truncate_content` (`utils.py:257-265`).
**Signature:** `MAX_OPERATIONS=10_000_000`, `MAX_WHILE_ITERATIONS=1_000_000`, `MAX_EXECUTION_TIME_SECONDS=30`, `DEFAULT_MAX_LEN_OUTPUT=50_000`; `evaluate_python_code(..., max_print_outputs_length, timeout_seconds=None-to-disable)`.
**Data Shape:** Counter lives IN the shared state dict under `_operations_count: {"counter": int}` (survives across the whole program because state is passed by reference; executor-level state persists it across steps too); print outputs accumulate in `state["_print_outputs"] = PrintContainer()` (string-like via `__iadd__`/`__str__`/`__len__`).

### Decisive source
```python
# :289-301 — cross-platform timeout docstring carries the caveat:
#   "If a timeout occurs, the thread running the function cannot be forcefully killed
#    in Python, so it will continue running in the background until completion."
with ThreadPoolExecutor(max_workers=1) as executor:
    future = executor.submit(func, *args, **kwargs)
    try:    result = future.result(timeout=timeout_seconds)
    except FuturesTimeoutError:
        raise ExecutionTimeoutError(f"Code execution exceeded the maximum execution time of {timeout_seconds} seconds")
```

**Flow:** Every single `evaluate_ast` dispatch increments and checks the op counter (catches huge pure-computation loops even when each statement is cheap); `while` has an extra iteration ceiling checked AFTER each pass; the whole program runs inside one fresh-per-call ThreadPoolExecutor so wall-clock >30s raises `ExecutionTimeoutError`; on every exit path (normal/final/error) `_print_outputs.value` is replaced by `truncate_content(str(...), max_print_outputs_length)` — head-half + marker + tail-half at `utils.MAX_LENGTH_TRUNCATE_CONTENT=20000` default for observations.
**Invariant:** The four budgets are complementary, not redundant: op-count stops CPU-bound loops that finish "in time", timeout stops I/O-bound hangs the counter can't see, while-cap exists because a `while` body of one node burns only 1 op/iteration, truncation protects the LLM context window not memory. The timeout's zombie-thread caveat is documented behavior — never port it as a hard kill.
**Probe:** `tests/test_local_python_executor.py::TestTimeout.test_timeout_decorator_raises_error_when_exceeded` (:2190-2198, matches message text), `test_max_operations` (:392), `test_while` infinite-loop case (:648+). Live: `@timeout(1)`-decorated sleep(3) → ExecutionTimeoutError with exact message.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-smolagents", query: "MAX_OPERATIONS timeout ExecutionTimeoutError operations_count", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt all four fences plus the honest zombie-thread note. Adapt numeric limits to your host's patience. Omit signal-based timeouts (the decorator explicitly rejects them for Windows/thread-safety).
