<!-- capsule-v2 -->
# derive_from_rows — one bounded-parallelism map primitive whose errors are collected, reported, and only THEN thrown

**Source:** graphrag MIT `main@60668ba946ccfd5cb784c578efedff86798a2c35`; Codebase Memory `graphrag`. **Question:** how does every heavy indexing operation (extract graph, covariates, community reports) share one concurrency primitive, and what exactly happens when a single row fails mid-fan-out?

## Connected graph-selected seam
**Path/Symbol:** `packages/graphrag/graphrag/index/utils/derive_from_rows.py`: `derive_from_rows` (:222-243), `derive_from_rows_asyncio_threads` (:246-273), `derive_from_rows_asyncio` (:276-304), `_derive_from_rows_base` (:313-355), `ParallelizationError` (:212-219).
**Signature:** `derive_from_rows(input: pd.DataFrame, transform: Callable[[pd.Series], Awaitable[ItemType]], callbacks, num_threads: int = 4, async_type: AsyncType = AsyncType.AsyncIO, progress_msg: str = "") -> list[ItemType | None]`.
**Data Shape:** result list is INDEX-ALIGNED with input rows; failed rows hold `None` until the final throw. Errors collect as `(exception, traceback_string)` tuples.

### Decisive source
```python
async def execute(row):
    try:
        result = transform(row[1])
        if inspect.iscoroutine(result):
            result = await result          # accepts sync AND async transforms
    except Exception as e:
        errors.append((e, traceback.format_exc()))
        return None                        # failure becomes a None SLOT
    else:
        return result
    finally:
        tick(1)                            # progress advances even on failure
...
result = await gather(execute)             # FULL fan-out completes first
for error, stack in errors:
    logger.error("parallel transformation error", exc_info=error, extra={"stack": stack})
if len(errors) > 0:
    raise ParallelizationError(len(errors), errors[0][1])  # AFTER the dust settles
```

**Flow:** dispatch by `AsyncType` — `AsyncIO` creates semaphore-guarded tasks directly on the loop; `Threaded` wraps each execution in `asyncio.to_thread` with the SAME semaphore acquired around thread start AND await; unknown enum raises ValueError immediately. Every row runs through the protected executor; gather always runs to completion; only afterward are errors logged en masse and a `ParallelizationError(count, first_traceback)` raised. Callers like `extract_graph` see the throw only after all other rows finished.
**Invariant:** (1) one row's failure never cancels siblings — cancellation-free collection is the point. (2) Progress ticks exactly once per row regardless of outcome. (3) Concurrency is bounded by `asyncio.Semaphore(num_threads or 4)` in BOTH modes; Threaded mode holds the slot across the thread handoff so in-flight threads ≤ num_threads. (4) Sync transforms are legal — the primitive awaits only when `iscoroutine`.
**Probe:** no dedicated unit test file for this util (exercised indirectly through every operation test, e.g. `tests/unit/indexing/operations/test_extract_graph.py` drives it via `extract_graph`). Coverage caveat recorded: error-collection ordering pinned by source read, not a direct test.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "graphrag", query: "derive_from_rows ParallelizationError AsyncType Threaded semaphore progress_ticker", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt collect-then-throw bounded fan-out as the standard runner for per-item LLM work (it converts partial failures into one actionable report instead of losing completed rows); adapt scheduler choice (loop vs threads) to host. Do NOT "fix" the post-gather throw into a mid-flight cancel — downstream callers rely on full completion semantics.
