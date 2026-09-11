<!-- capsule-v2 -->
# sqlstore idempotent writes — why can concurrent writers never duplicate versions or corrupt counts?

**Source:** ell MIT `main@9d129846203e75efeb4e5cddd3fb1c164dc0b243`; Codebase Memory `ext-ell`. **Question:** What write discipline makes a shared SQLite/Postgres LMP store safe under parallel tracked calls?

## check-then-insert with IntegrityError rollback + count-in-transaction
**Path/Symbol:** `src/ell/stores/sql.py:SQLStore.write_lmp` (:52-81), `write_invocation` (:83-116); engine construction with custom json_serializer (:36-50).
**Signature:** `write_lmp(self, serialized_lmp: SerializedLMP, uses: Dict[str, Any]) -> Optional[Any]`; `write_invocation(self, invocation: Invocation, consumes: Set[str]) -> Optional[Any]`.
**Data Shape:** `SerializedLMPUses` link table (lmp_user_id, lmp_using_id) both PK+FK; `InvocationTrace` (consumer, consuming) both PK.

### Decisive source
```python
# sql.py:55-81
with Session(self.engine) as session:
    try:
        lmp = session.exec(
            select(SerializedLMP).filter(
                SerializedLMP.lmp_id == serialized_lmp.lmp_id
            )
        ).first()

        if lmp:
            # Already added to the DB.
            return lmp
        else:
            session.add(serialized_lmp)

        for use_id in uses:
            used_lmp = session.exec(
                select(SerializedLMP).where(SerializedLMP.lmp_id == use_id)
            ).first()
            if used_lmp:
                serialized_lmp.uses.append(used_lmp)

        session.commit()
        return None
    except sqlalchemy.exc.IntegrityError as e:
        session.rollback()
        return None
```

**Flow:** version writes are idempotent by lmp_id (content hash): pre-check short-circuits duplicates, and the UNIQUE constraint catches the race window — rollback and return None instead of raising, because "already written by a sibling thread" is success for the caller. Use edges append only rows that EXIST (unknown use ids silently skipped — never FK-fail the whole write). Invocation writes are one transaction: assert the parent LMP exists, increment `num_invocations` on it (None→1 ladder), add contents + invocation + one InvocationTrace per consumed id, commit together.
**Invariant:** every JSON-bearing column flows through the engine-level `json_serializer` using `pydantic_ltype_aware_cattr.unstructure` + sort_keys — row bytes are canonical, so equality checks and diffs are stable across processes.
**Probe:** `tests/test_sql_store.py:test_write_lmp` (:21-78) executes the double-write path and pins single-row outcome (`select(func.count())...one()` after second write) plus tz-aware `created_at`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ell", query: "write_lmp IntegrityError", limit: 5, fields: ["signature", "name", "file"] });
// rank-2: ext-ell.src.ell.stores.sql.SQLStore.write_lmp @ src/ell/stores/sql.py:52-81
```

## Verdict
Adopt idempotent-by-content-hash writes with constraint-violation-as-success semantics. Adapt the use-edge policy if your schema requires strict FK integrity (upstream prefers availability). Omit nothing from the transactional grouping in `write_invocation` — splitting the counter bump from the row insert is how counters drift.
