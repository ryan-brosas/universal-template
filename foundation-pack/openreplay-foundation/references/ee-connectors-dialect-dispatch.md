<!-- capsule-v2 -->
# EE connectors worker pool + dialect dispatch — how do decoded session messages fan out to five warehouse SQL dialects?

**Source:** openreplay AGPL-3.0 `main@99eb600` — **ee/ is Enterprise-licensed; patterns only, no code copying**; Codebase Memory `openreplay`. **Question:** What architecture shape routes a decoded event batch to ClickHouse/Postgres/Redshift/BigQuery/Snowflake with pandas?

## Import-time dialect switch + process-pool workers
**Path/Symbol:** `ee/connectors/db/writer.py` (:1–92: CLOUD_SERVICE import-time branch, `insert_batch`, `update_batch` f-string UPDATE builder); pool `ee/connectors/utils/worker.py` (`WorkerPool:378+`, `decode_message:264–296`, `ProjectFilter:96–149`, checkpoint `load_checkpoint`), entrypoint `ee/connectors/consumer_pool.py` (env `OR_EE_CONNECTOR_WORKER_COUNT` default 60).
**Signature:** `insert_batch(db, batch, table, level='normal')`; `decode_message(params) → (events, memory, ended_ids)`.
**Data Shape:** Kafka message → `codec.decode_detailed` → typed Session/Event objects; per-session memory dict of mutable Session rows; `sessionid_ended` list drives row close.

### Decisive source
```python
if DATABASE == 'redshift':   from db.loaders.redshift_loader import transit_insert_to_redshift
elif DATABASE == 'clickhouse': from db.loaders.clickhouse_loader import insert_to_clickhouse
...
def insert_batch(db, batch, table, level='normal'):
    df = get_df_from_batch(batch, level=level)
    if db.config == 'redshift': transit_insert_to_redshift(...)
    if db.config == 'clickhouse': insert_to_clickhouse(...)
```

**Flow:** consumer reads raw topic → hash session_id to a worker process → worker decodes, folds messages into in-memory Session state (SessionEnd marks completion) → completed/periodic batches become DataFrames → dialect loader inserts. UPDATE path builds a parameterized SET clause from a static dtype map (`dtypes_sessions`) skipping the sessionid key.
**Invariant:** Dialect selection is IMPORT-TIME by design — one deployment serves one warehouse; runtime switching is not supported and must not be "fixed". Redshift UPDATE string-building quotes strings vs bare numerics by dtype.
**Probe:** `grep -cF 'len(batch) == 0' ee/connectors/db/writer.py` → `2`; `grep -c 'decode_detailed' ee/connectors/utils/worker.py` → `1`; `grep -c 'OR_EE_CONNECTOR_WORKER_COUNT' ee/connectors/consumer_pool.py` → `1`. Direct tests: none upstream for ee connectors (coverage caveat).
**Coverage:** cited files clean.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "openreplay", query: "insert_batch decode_message WorkerPool clickhouse_loader", limit: 10 });
```

## Verdict
Adopt worker-per-session-hash + DataFrame boundary. Adapt loaders per warehouse. Omit redshift transit staging if direct inserts suffice.
