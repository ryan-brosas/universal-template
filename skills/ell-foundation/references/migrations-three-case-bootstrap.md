<!-- capsule-v2 -->
# migrations three-case bootstrap — how does a fresh, pre-alembic, or stale database converge to head safely?

**Source:** ell MIT `main@9d129846203e75efeb4e5cddd3fb1c164dc0b243`; Codebase Memory `ext-ell`. **Question:** How do I ship a versioned schema to users whose existing databases predate my migration tooling?

## table-set intersection decides stamp vs create vs upgrade
**Path/Symbol:** `src/ell/stores/migrations/__init__.py:init_or_migrate_database` (:24-82), `get_alembic_config` (:12-21); custom `version_table="ell_alembic_version"`.
**Signature:** `init_or_migrate_database(engine) -> None`.
**Data Shape:** v1 table set = `{serializedlmp, invocation, invocationcontents, invocationtrace, serializedlmpuses}`; v2 marker set = the four evaluation tables; revisions: initial `4524fb60d23e`, head (evaluations) `f6528d04bbbd`.

### Decisive source
```python
# migrations/__init__.py:42-52 and 70-78
has_our_tables = bool(our_tables_v1 & existing_tables)  # Intersection
has_alembic = 'ell_alembic_version' in existing_tables
...
if has_our_tables and not has_alembic:
    is_v1 = has_our_tables and not bool(our_tables_v2 & existing_tables)
    command.stamp(alembic_cfg, "4524fb60d23e" if is_v1 else "head")
...
else:
    # New database detected - creating schema and stamping with latest migration
    SQLModel.metadata.create_all(engine)
    command.stamp(alembic_cfg, "head")
```

**Flow:** Case 1 — tables but no alembic bookkeeping (pre-0.14 user): infer era by whether eval tables exist; v1 stamps the INITIAL revision so pending migrations then run; v2-era stamps head. Post-stamp verification re-reads `ell_alembic_version` for the v1 path and raises RuntimeError if the stamp silently failed. Case 2 — alembic present: plain `upgrade head`. Case 3 — empty/foreign DB: `SQLModel.metadata.create_all` builds CURRENT schema directly, then stamp head (create_all and migrations must agree — pinned by a schema-equality test that sorts recursively before comparing).
**Invariant:** never run migrations on top of a schema that was just created by metadata — stamp only; and the version table must be namespaced (`ell_alembic_version`) so co-tenant alembic setups don't collide.
**Probe:** `tests/test_migrations.py:test_empty_db_migration` (:75-, create_all == migrated schema equality); `test_existing_tables_no_alembic` (:101-119, pins stamped revision `f6528d04bbbd` when eval tables present); `test_migration_idempotency` (:155-) pins second init as no-op.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ell", query: "init or migrate database alembic", limit: 5, fields: ["signature", "name", "file"] });
// rank-1: ext-ell.src.ell.stores.migrations.init_or_migrate_database @ src/ell/stores/migrations/__init__.py:24-82
```

## Verdict
Adopt intersection-based era detection with post-stamp verification. Adapt revision ids and marker-table sets per your history. Omit nothing from the three-case structure — collapsing case 1 into case 3 is what destroys legacy user data.
