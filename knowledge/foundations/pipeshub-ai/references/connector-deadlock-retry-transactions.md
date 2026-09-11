<!-- capsule-v2 -->
# Deadlock-retrying transactions — how do multi-edge record writes survive Neo4j deadlocks without the connector knowing?

**Source:** PipesHub AI Apache-2.0 `main@c28d1336`; Codebase Memory `mnt-hdd-utopia-inspo-platforms-pipeshub-ai`. **Question:** Where should retry live for transactional record ingestion: inside every vendor adapter, or once at the store boundary?

## Decorator-level re-execution with exponential backoff
**Path/Symbol:** `backend/python/app/connectors/core/base/data_store/graph_data_store.py:` `_is_deadlock_error` (:38-56), `retry_on_deadlock(max_retries=3)` (:59-110), `GraphTransactionStore` (:120+), `GraphDataStore.transaction()` context manager.
**Signature:** `def retry_on_deadlock(max_retries=3)` wrapping async funcs; backoff `0.1 * (2 ** attempt)`; `_is_deadlock_error(e) -> bool` matches `TransientError`+`"DeadlockDetected"` with import-guard fallback when neo4j absent.
**Data Shape:** `TransactionStore` mirrors the full write API with an injected `txn` id (HTTP-provider transactions); `DataStoreProvider.compare_and_set_indexing_status(ids, expected, new) -> list[str]` documented as deliberately NON-transactional.

### Decisive source
```python
for attempt in range(max_retries):
    try:
        return await func(*args, **kwargs)
    except Exception as e:
        last_exception = e
        if _is_deadlock_error(e) and attempt < max_retries - 1:
            backoff = 0.1 * (2 ** attempt)   # 0.1s, 0.2s, 0.4s
            logger.warning(f"Deadlock detected in {func.__name__} "
                f"(attempt {attempt + 1}/{max_retries}), retrying in {backoff:.1f}s: ...")
            await asyncio.sleep(backoff)
            continue
```
Decorator usage pattern:
```python
@retry_on_deadlock(max_retries=3)
async def on_new_records(self, records_with_permissions):
    async with self.data_store_provider.transaction() as tx_store:
        ...   # whole handler re-executes → fresh transaction naturally
```

**Flow:** any `DataSourceEntitiesProcessor.on_*` handler decorated → deadlock detected by exception shape (works even without the driver installed via string match) → sleep-backoff → ENTIRE function re-runs, opening a new transaction; non-deadlock errors raise immediately; exhaustion logs "Deadlock persists" then raises. Import guard keeps the module loadable where neo4j isn't installed (unit-testable pure logic).
**Invariant:** Retry granularity is the WHOLE handler, not individual statements — re-execution must be idempotent, which the record-upsert kernel guarantees (upsert-by-external-id, CAS statuses). The CAS status writer is intentionally outside transactions ("races the indexing service... read and write in one statement") — never move it inside a retried txn.
**Probe:** `grep -c '0.1 \* (2 \*\* attempt)' app/connectors/core/base/data_store/graph_data_store.py` → `1`; suite `tests/unit/connectors/core/test_graph_data_store.py::TestRetryOnDeadlock` (:845-924: detects/rejects/retries/no-retry-on-non-deadlock) ALL GREEN in battery.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-pipeshub-ai", query: "retry_on_deadlock TransientError", limit: 3 });
```
(rank #1 Function `graph_data_store.py` :59-110.)
**Verdict:** Adopt decorator-at-boundary + idempotent-handler pairing; adapt detection strings to host DB's transient-error signature; omit neo4j import specifics (keep the fallback matcher).
