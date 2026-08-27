<!-- capsule-v2 -->
# Alembic Orphan-Recovery Migration — how to recover a deployment whose migration files were deleted upstream

**Source:** awaithumans Apache-2.0 `main@bc05b8e7`; Codebase Memory `mnt-hdd-utopia-inspo-awaithumans`. **Question:** When shipped migration files are deleted from the repo, every deployed DB is stamped at a revision alembic can no longer locate — what does the durable repair look like?

## Connected graph-selected seam
**Path/Symbol:** `packages/python/alembic/versions/20260622_0530_drop_orphaned_demo_records.py` (whole file, :1-84; revision `4c51f4e2d8f9`, down_revision `8b4ed1c70a5f`). Census: exactly 16 alembic-related files at this pin (ini, env, baseline + schema adds + ONE merge-heads + this recovery head).
**Signature:** `def upgrade() -> None` / `def downgrade() -> None` over `op.get_bind().dialect.name`.
**Data Shape:** orphaned table `demo_records` + Postgres ENUM `demostatus` left physically present by PR #184→#186 while `alembic_version` still pointed at the deleted revision.

### Decisive source
```python
    bind = op.get_bind()
    dialect = bind.dialect.name

    op.execute("DROP TABLE IF EXISTS demo_records")

    # The ENUM type is Postgres-specific; SQLite stores enums as
    # CHECK constraints inline with the column and there's nothing
    # left to clean up once the table is gone.
    if dialect == "postgresql":
        op.execute("DROP TYPE IF EXISTS demostatus")
```
And the no-op downgrade that still executes something (:82-84):
```python
    # Use a SQL comment so alembic still emits an executable
    # statement (some pgbouncer pools error on empty transactions).
    op.execute("-- drop_orphaned_demo_records: downgrade is a no-op")
```

**Flow:** upstream deleted the demo migrations along with the code → every existing OSS Postgres kept `alembic_version = '20260606_2000_demo_records_dynamic_schema'` → container start ran `upgrade head` → "Can't locate revision" → reviewers Container App crash-looped. Interim prod fix was a manual stamp-back to the last surviving revision; THIS migration then ships as the new head and tidies the leftovers.
**Invariant:** the cleanup must be idempotent (`IF EXISTS` on both DROPs) because fresh post-PR-186 deployments never had the table and must still apply the head cleanly; the ENUM drop is dialect-gated (Postgres TYPE vs SQLite inline CHECK); downgrade is a DOCUMENTED no-op that still emits an executable statement because some pgbouncer pools reject empty transactions. The docstring records the whole incident so operators understand why the objects exist to be dropped.

**Probe:** none upstream (migrations carry no tests) — recorded caveat. Line-checked byte-exact at pin: IF EXISTS :67/:73, dialect gate :72, executable-comment downgrade :82-84, down_revision `8b4ed1c70a5f` :51. Graph census reproduced live: query_graph File CONTAINS 'alembic' = exactly 16 rows.

## Get live surrounding code
**Retrieve:**
```ts
// Census (graph): enumerate every alembic file
await mcp.codebase_memory.query_graph({ project: "mnt-hdd-utopia-inspo-awaithumans", query: "MATCH (f:File) WHERE f.file_path CONTAINS 'alembic' RETURN f.file_path ORDER BY f.file_path" });
```
Live at pin: 16 rows — ini/env/baseline, nine schema-add migrations, one merge-heads node (`20260508_1819_merge_embed_and_webhook_deliveries_heads`, textbook empty pass/pass), and this recovery head.

## Verdict
Adopt the recovery playbook: stamp-back to the last surviving revision, THEN ship an idempotent IF-EXISTS cleanup migration as the new head with a full incident docstring; gate vendor DDL by dialect; make even no-op downgrades emit executable SQL for pool compatibility. Adapt object names/dialects. Omit the docstring and your future operators will re-derive the whole incident from git archaeology.
