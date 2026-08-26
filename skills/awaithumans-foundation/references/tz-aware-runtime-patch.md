<!-- capsule-v2 -->
# Tz-Aware Timestamp Runtime Patch — how do you repair a deployed schema's naive columns without a new migration?

**Source:** awaithumans Apache-2.0 `main@bc05b8e7`; Codebase Memory `mnt-hdd-utopia-inspo-awaithumans`. **Question:** When old migrations created `TIMESTAMP WITHOUT TIME ZONE` but the service writes tz-aware UTC, how does startup fix prod without deploy-coupled ALTERs?

## information_schema-checked idempotent ALTER at boot
**Path/Symbol:** `packages/python/awaithumans/server/db/connection.py` — `_NAIVE_TIMESTAMP_COLUMNS` (:28–52), `init_db` (:139–157), `_patch_naive_timestamp_columns/_alter_naive_timestamps` (:166–248).
**Signature:** `_alter_naive_timestamps(conn, columns) -> int` (count altered; second boot ⇒ 0); outer function short-circuits unless URL startswith postgresql.
**Data Shape:** 22 (table, column) pairs across tasks/users/webhook_deliveries/audit/slack/email tables; checked against information_schema, never used as a positive allowlist.

### Decisive source
```sql
ALTER TABLE "{table}" ALTER COLUMN "{column}" TYPE TIMESTAMP WITH TIME ZONE
    USING "{column}" AT TIME ZONE 'UTC'
```
```python
current_type = (await conn.execute(text(
    "SELECT data_type FROM information_schema.columns "
    "WHERE table_name = :t AND column_name = :c"), {"t": table, "c": column})).scalar_one_or_none()
if current_type is None:                        continue   # dropped/renamed → alembic owns lifecycle
if current_type != "timestamp without time zone": continue  # already patched or born-correct
```

**Flow:** alembic upgrade head runs in `asyncio.to_thread` (alembic is sync; never block the loop) ⇒ patch sweeps the pair list ⇒ AT TIME ZONE 'UTC' LABELS existing values as the UTC they always were (value-preserving — service layer wrote `datetime.now(timezone.utc)` throughout) ⇒ asyncpg can now bind tz-aware datetimes and the timeout/webhook schedulers stop crashing every tick. SQLite skipped entirely (no information_schema; bug never manifested).
**Invariant:** runtime patch INSTEAD of an alembic revision — idempotent so booting an already-patched server is free, and once every deployment has booted under PR 6 the list is stable and deletable. Quoted identifiers defend against future case renames. The inner/outer split exists purely so tests can mock the connection.
**Probe:** `tests/server/test_tz_aware_postgres_datetimes.py` (:99 all model datetime columns tz-aware, :121 patch list covers every tz-aware column — keeps the two lists in lockstep, :164–240 sqlite/non-pg no-op + SQL shape, :283–357 already-tz skip / missing-column skip / mixed batch / pre-PR6-schema match).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-awaithumans", query: "_patch_naive_timestamp_columns alter", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt check-then-ALTER idempotent repair, value-preserving timezone labeling, thread-offloaded sync migrations, and the paired model-columns↔patch-list completeness test. Adapt column inventory. Omit the specific alembic layout resolution (_alembic_paths) if your packaging differs.
