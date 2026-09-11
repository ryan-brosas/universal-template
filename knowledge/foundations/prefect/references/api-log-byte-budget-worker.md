<!-- capsule-v2 -->

# APILogWorker byte-budget batching — How do you batch log uploads by payload BYTES with per-settings worker identity?

**Source:** prefect Apache-2.0 `main@ce79dd3d6cfa2b7337265498210dbc4d25bcdc98`; Codebase Memory `prefect`. **Question:** How does the API log shipper size its batches in bytes, key its singleton on settings, and fail without retrying?

## Batch budget = max(BATCH_SIZE − MAX_LOG_SIZE, MAX_LOG_SIZE); failure writes to stderr and DROPS

**Path/Symbol:** `src/prefect/logging/handlers.py:APILogWorker (67-110)` — `max_batch_size (68-74)`, `min_interval (76-78)`, `_handle_batch (80-91)`, `_lifespan (93-96)`, `instance (98-107)`, `_get_size (109-110)`.

**Signature:** `APILogWorker(BatchedQueueService[Dict[str, Any]])`; items are `LogCreate.model_dump(mode="json")` dicts carrying a private `__payload_size__` int.

**Data Shape:** settings read LIVE: `PREFECT_LOGGING_TO_API_BATCH_SIZE` (byte budget), `PREFECT_LOGGING_TO_API_MAX_LOG_SIZE` (per-log cap), `PREFECT_API_URL`, `PREFECT_LOGGING_TO_API_BATCH_INTERVAL`.

### Decisive source
```python
@property
def max_batch_size(self) -> int:
    return max(
        PREFECT_LOGGING_TO_API_BATCH_SIZE.value()
        - PREFECT_LOGGING_TO_API_MAX_LOG_SIZE.value(),
        PREFECT_LOGGING_TO_API_MAX_LOG_SIZE.value(),
    )

async def _handle_batch(self, items: list[dict[str, Any]]):
    try:
        await self._client.create_logs(items)
    except Exception as e:
        # Roughly replicate the behavior of the stdlib logger error handling
        if logging.raiseExceptions and sys.stderr:
            sys.stderr.write("--- Error logging to API ---\n")
            if PREFECT_LOGGING_INTERNAL_LEVEL.value() == "DEBUG":
                traceback.print_exc(file=sys.stderr)
            else:
                sys.stderr.write(str(e))

@classmethod
def instance(cls, *args):
    settings = (
        PREFECT_LOGGING_TO_API_BATCH_SIZE.value(),
        PREFECT_API_URL.value(),
        PREFECT_LOGGING_TO_API_MAX_LOG_SIZE.value(),
    )
    # Ensure a unique worker is retrieved per relevant logging settings
    return super().instance(*settings, *args)

def _get_size(self, item):
    return item.pop("__payload_size__", None) or len(json.dumps(item).encode())
```

**Flow:** emit-time dict carries a precomputed `__payload_size__`; the worker batches until cumulative popped byte-size reaches the budget or the interval window closes; `_lifespan` holds ONE `get_client()` httpx session for the worker's whole life. On upload failure there is NO retry — the batch is lost and a stdlib-style stderr note is written (traceback only at internal DEBUG). Changing any of the three keyed settings yields a DIFFERENT worker instance rather than silently reusing stale-configured clients.

**Invariant:** (1) The budget floor at `MAX_LOG_SIZE` guarantees at least one max-sized log fits per batch. (2) `__payload_size__` is POPPED during sizing so the private key never ships to the API; recomputing via `json.dumps` is only a fallback for hand-built dicts. (3) Logs are lossy-tolerant by design — contrast events-websocket-resend-checkpoint where delivery is buffered and resent.

**Probe:** direct tests `tests/test_logging.py:1218 test_send_logs_batches_by_size` (budget = size+1 ⇒ 3 separate create_logs calls), `:1199 test_send_logs_writes_exceptions_to_stderr` (`--- Error logging to API ---` + message), `:1242/:1263 test_logs_are_sent_immediately_when_{stopped,flushed}` (10 s interval beaten by drain), `:2456 test_prepare_truncates_oversized_log`.

## Get live surrounding code
**Retrieve:**
```bash
codebase-memory-mcp cli search_graph '{"project": "prefect", "name_pattern": "^(APILogWorker|emit_api_log|set_api_log_sink)$", "limit": 5}'
```
(observed: `APILogWorker Class src/prefect/logging/handlers.py 67-110`; `emit_api_log Function 59-64` routes through an optional sink override before `instance().send`)

## Verdict
Adopt byte-budgeted batching with settings-keyed service identity and drop-on-error stderr reporting for lossy-tolerant telemetry; adapt setting names/units; omit the sink-override hook unless you need subprocess log forwarding.
