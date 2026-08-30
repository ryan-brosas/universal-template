<!-- capsule-v2 -->
# Disk-backed OTLP retry — how do failed exports survive network outages without unbounded memory?

**Source:** logfire MIT `main@e484a6b5`; Codebase Memory `ext-logfire`. **Question:** What is the full retry choreography for a failed OTLP POST, and what bounds memory, disk, log spam, and duplicate sends?

## OTLPExporterHttpSession.post → DiskRetryer
**Path/Symbol:** `logfire/_internal/exporters/otlp.py:OTLPExporterHttpSession.post` (`otlp.py:80-133`) + `DiskRetryer._run` (`otlp.py:236-279`).
**Signature:** `post(self, url: str, data: bytes, **kwargs) -> Response`; `DiskRetryer(headers: Mapping[str, str | bytes])`.
**Data Shape:** retry task = `(Path, kwargs-dict)` in a bounded deque; body bytes written to `mkdtemp(prefix='logfire-retryer-')/<uuid4.hex>`; budget `MAX_TASK_SIZE = 512 * 1024 * 1024`; backoff delay ∈ [2, MAX_DELAY=128] seconds; logs throttled to once per `LOG_INTERVAL=60`s.

### Decisive source
```python
def post(self, url, data, **kwargs):
    self._configure_timeout(kwargs)          # (min(HTTP_CONNECT_TIMEOUT=3, t), t)
    start_time = time.time()
    try:
        return self._post(url, data, **kwargs)
    except requests.exceptions.RequestException as e:
        end_time = time.time()
        if end_time - start_time > 10:        # first attempt already slow -> straight to disk
            self._add_task(data, url, kwargs, e); raise
        time.sleep(1)                          # cheap backpressure before disk
        try:
            return self._post(url, data, **kwargs)
        except requests.exceptions.RequestException as e2:
            self._add_task(data, url, kwargs, e2); raise
```
and in `_run`: `time.sleep(delay * (1 + random.random()))` (proportional jitter so post-outage retries spread across MAX_DELAY), failure ⇒ `delay = min(delay*2, 128)` floored at 2; success ⇒ `delay = 0.2`, unlink file, decrement total_size. ConnectionError is re-raised as `SuppressedConnectionError` because "OTel already retries ConnectionError … would create two layers of retrying and lead to duplicate exports". `raise_for_retryable_status` re-raises on 408/429/5xx.
**Flow:** POST fails fast (<10s) → one 1s-delayed retry → spill to DiskRetryer (daemon thread started lazily via `cached_property`) → exponential backoff with jitter until success or close → `close()` sets closed=True, empties deque (`deque(maxlen=0)`), zeroes size, rmtree's the temp dir. Global `_DISK_RETRYERS: list[weakref.ref]` + `@atexit cleanup_disk_retryers` guarantees directory cleanup even without explicit close. Budget check happens under the lock BEFORE writing the file; write failure refunds total_size under the lock.
**Invariant:** The retryer thread is a daemon deliberately (may never finish on exit — documented caveat). The session posted-to from the retryer is a FRESH plain Session ("thread safety of Session is questionable"), sharing only headers. The 10-second first-attempt threshold balances queue-fill risk vs shutdown-deadline risk — both are commented in source.
**Probe:** `tests/test_otlp_exporter.py` — pins retry-on-connection-error, disk spill, and SuppressedConnectionError dedupe behavior.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-logfire", query: "DiskRetryer add_task _run MAX_TASK_SIZE SuppressedConnectionError", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt: two-tier retry (sleep-then-disk), proportional-jitter backoff with success-reset, byte-budgeted disk queue, weakref+atexit cleanup, ConnectionError dedupe vs OTEL's own retry. Adapt the HTTP client/session types. Omit the Emscripten guard only if your host always has threads.
