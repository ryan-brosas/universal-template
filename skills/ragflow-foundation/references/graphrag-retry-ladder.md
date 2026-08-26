<!-- capsule-v2 -->
# GraphRAG phase retry ladder — how do per-phase timeouts, bounded backoff, and cancellation coexist without retrying a dead task?

**Source:** ragflow Apache-2.0 `main@9ea83b7a9d003d948fe4c99c6f35de02115a96e8`; Codebase Memory `ragflow`. **Question:** What is the exact retry/timeout/backoff contract for each GraphRAG phase, and which exceptions must never be retried?

## Coro-factory retry with cancel passthrough
**Path/Symbol:** `rag/graphrag/general/index.py:_run_with_retry` (:149-187); `_bounded_int_config`/`_bounded_float_config` (:77-104); `_acquire_lock` (:190-206).
**Signature:** `async def _run_with_retry(label: str, coro_factory, *, attempts: int, timeout_seconds: int | float, backoff_seconds: float, backoff_max_seconds: float, callback=None, task_id: str = "")`.
**Data Shape:** `coro_factory` is a zero-arg callable producing a FRESH coroutine per attempt; config values come from `kb_parser_config["graphrag"]` clamped by `_bounded_*_config`. Defaults at pin: attempts=2, backoff 2s capped 60s, merge 180s, resolution/community 1800s, lock acquire 600s.

### Decisive source
```python
for attempt in range(1, attempts + 1):
    _has_cancel_and_exit(task_id, f"Task {task_id} cancelled before {label}.", callback)
    try:
        if timeout_seconds and timeout_seconds > 0:
            return await asyncio.wait_for(coro_factory(), timeout=timeout_seconds)
        return await coro_factory()
    except (TaskCanceledException, asyncio.CancelledError):
        raise                      # never retried
    except asyncio.TimeoutError as e:
        last_error = e
    except Exception as e:
        last_error = e
    ...
    wait = min(backoff_max_seconds, backoff_seconds * (2 ** (attempt - 1)))
```
```python
# clamp-to-DEFAULT, not clamp-to-bound:
if value < minimum or value > maximum:
    logging.warning("Invalid GraphRAG config %s=%r, using default %s", key, value, default)
    return default
```

**Flow:** each phase call site wraps its work in `_run_with_retry("build_subgraph doc:X" / "merge_subgraph doc:X" / "entity resolution" / "community extraction", ...)` → cancel checked before EVERY attempt and inside `_acquire_lock`'s poll loop → TimeoutError counts as a failed attempt and is retried like any error → after the final attempt the LAST error is re-raised to the caller, which records `(doc_id, reason)` into `failed_docs` or aborts.
**Invariant:** Cancellation (`TaskCanceledException`/`CancelledError`) propagates immediately through every retry layer; backoff grows geometrically but is capped; out-of-range user config falls back to the default rather than the nearest bound; the KB merge/post-merge sections hold a `RedisDistributedLock(f"graphrag_task_{kb_id}")` acquired only through the cancellable poll loop (deadline ⇒ `asyncio.TimeoutError`).

## Get live surrounding code
**Retrieve:** (executed this pass)
```ts
await mcp.codebase_memory.search_graph({ project: "ragflow", query: "run_graphrag_for_kb merge graph community resolution cancel", filePattern: "*index.py", fields: ["lines","signature"] });
// rank-1 run_graphrag_for_kb :256-644, rank-3 _has_cancel_and_exit :141-146
```

## Verdict
Adopt the coro-factory shape (fresh attempt closure so partial state can't leak between tries), cancel-passthrough, capped exponential backoff, and clamp-to-default config parsing; adapt defaults/timeouts and the Redis lock primitive to your host; omit the specific callback-message strings. Direct-test caveat: this ladder has no dedicated unit test file at the pin — evidence is source-only (index.py read in full) plus its use inside tested flows.
