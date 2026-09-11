<!-- capsule-v2 -->
# Tz-Aware Timestamp Columns — why does every datetime column need `timezone=True` at declaration time, and what does the scheduler get from it?

**Source:** awaithumans Apache-2.0 `main@bc05b8e7`; Codebase Memory `mnt-hdd-utopia-inspo-awaithumans`. **Question:** How do you guarantee asyncpg can bind tz-aware datetimes forever — not just repair legacy columns after the schedulers crash?

## Declaration-side law of the two-half TZ contract
**Path/Symbol:** `packages/python/awaithumans/server/db/models/base.py:tz_timestamp_column` (:21–51); consumer `packages/python/awaithumans/server/services/timeout_scheduler.py:_check_and_timeout_expired_tasks` (:41–69); contract tests `packages/python/tests/server/test_tz_aware_postgres_datetimes.py`.
**Signature:** `tz_timestamp_column(*, nullable: bool = False, index: bool = False) -> Column`.
**Data Shape:** Returns a fresh `Column(DateTime(timezone=True), …)` per call. Without `timezone=True`, SQLModel emits plain `DateTime` → Postgres lands `TIMESTAMP WITHOUT TIME ZONE` → asyncpg refuses tz-aware binds and any `WHERE column <= now` dies with `can't subtract offset-naive and offset-aware datetimes`. SQLite ignores the hint (naive TEXT round-trip), so read-side `_ensure_utc` patterns stay necessary regardless.

### Decisive source
```python
# base.py — WHY a helper instead of inline sa_column args:
#   1. metadata.create_all (tests) produces tz-aware columns.
#   2. Future alembic autogenerate runs emit timezone=True.
#   3. Existing Postgres deployments are repaired at boot by
#      _patch_naive_timestamp_columns (see tz-aware-runtime-patch).
#
#   Each Field needs its own Column instance — don't cache the
#   return value or share it across fields, since SQLAlchemy mutates
#   Column state when binding to a Table.
return Column(DateTime(timezone=True), nullable=nullable, index=index)

# timeout_scheduler.py — the consumption that crashes when this law breaks:
result = await session.execute(
    select(Task.id)                                # ids only
    .where(Task.status.notin_(list(TERMINAL_STATUSES_SET)))
    .where(Task.timeout_at <= now)                 # indexed; tz-aware now()
)
```

**Flow:** model field declares `sa_column=tz_timestamp_column(...)` → `metadata.create_all` / alembic autogenerate emit TIMESTAMPTZ → service layer writes `datetime.now(timezone.utc)` throughout → scheduler compares `Task.timeout_at <= datetime.now(timezone.utc)` against an indexed column without bind errors → expired ids time out first-writer-wins (`timeout_task`), enqueue completion webhooks (dispatcher owns retries), swap Slack surfaces via detached `asyncio.create_task`.
**Invariant:** EVERY `DateTime` column in SQLModel.metadata MUST be `timezone=True` — pinned by `test_all_model_datetime_columns_are_tz_aware` walking all tables, so adding a bare `Field(default_factory=utc_now)` fails CI instead of silently reintroducing the prod crash on next Postgres deploy. Never share/cache one Column instance across fields (SQLAlchemy mutates it on Table bind).
**Probe:** `packages/python/tests/server/test_tz_aware_postgres_datetimes.py` (:77–96 pins the emitted column type/flags; :99–112 pins the no-naive-metadata walk). Deterministic source probe (runner-blocked run): `grep -n 'return Column(DateTime(timezone=True)' packages/python/awaithumans/server/db/models/base.py` → exactly :51.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-awaithumans", query: "tz_timestamp_column timeout_at scheduler due", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the declaration-law helper + its metadata-walk completeness test as ONE unit — the test is what makes the law survive new models. Adapt the paired boot-repair list to your schema inventory (`tz-aware-runtime-patch.md` owns that half). Omit SQLite-specific read normalization only if your store has real timestamptz types end-to-end.
