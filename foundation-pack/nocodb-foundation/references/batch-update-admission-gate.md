<!-- capsule-v2 -->
# Source
NocoDB `develop@640fe3b06fb26c9d000e2258477001c0d5e62c73` — `packages/nocodb/src/dbQueryClient/generic.ts` :104–113 + `db/BaseModelSqlv2.ts` :4499–4516 — the batchUpdate admission gate.

# Question
When does the record-update path take the single-statement batch vs the per-row loop, and what model property gates it?

## Path / Symbol
BaseModelSqlv2 bulk-update branch: `this.model.primaryKeys.length === 1 && (this.isPg || this.isMySQL || this.isSqlite || this.isMssql)`.

## Signature
```ts
await DBQueryClient.fromKnex(transaction).batchUpdate({ knex: transaction, tnPath: this.tnPath,
  rows: toBeUpdated.map(o => o.d), pkColumnName: this.model.primaryKey.column_name });
// else: for (const o of toBeUpdated) await transaction(this.tnPath).update(o.d).where(o.wherePk);
```

## Data Shape
Admission = composite predicate: exactly ONE primary key column AND dialect ∈ {pg, mysql, sqlite, mssql}. Oracle and multi-pk models always ride the loop.

## Decisive source
BaseModelSqlv2.ts:4500–4503 — the gate; note the dialect list EXCLUDES oracle even though oracle.ts could theoretically implement batchUpdate — because generic's CASE form is ORA-00932-fatal there (see batch-pk-update-case-funnel) and CE oracle throws EE_ONLY anyway. The client factory call is fromKnex(transaction) — the TRANSACTION, not the source connection — so the CASE statement participates in the caller's atomic unit (:4505 commit / :4510–4513 rollback with the "post-update hooks report success on data never written" comment).
Rows arrive pre-filtered as pure data dicts (`o.d`) — the undefined-row/pk guards inside batchUpdate are a SECOND line of defense, not the primary filter.

## Flow / Invariant
Porter rule: fast-path admission is a JOINT property of (schema shape, engine capability); encode it at the CALLER like upstream rather than inside the utility, so the utility stays total while callers choose. And always build the batch on the transaction handle — a pooled-connection factory here would orphan the CASE update outside rollback scope.

## Probe (direct test)
From repo root:
```
sed -n '104,128p' packages/nocodb/src/dbQueryClient/generic.ts | grep -c 'return null'   # => 4
grep -c 'primaryKeys.length === 1' packages/nocodb/src/db/BaseModelSqlv2.ts             # => 5 (batch-update gate is :4499; four other call sites exist elsewhere in the file)
grep -c 'isPg' packages/nocodb/src/db/BaseModelSqlv2.ts | head -1                       # >0; the batch gate combines all four on ONE line (:4500)
grep -n 'fromKnex(transaction)' packages/nocodb/src/db/BaseModelSqlv2.ts                # => 1 (:4502)
```

## Retrieve
```
codebase-memory-mcp cli search_graph '{"project":"mnt-hdd-utopia-inspo-platforms-nocodb","query":"batchUpdate transaction primaryKeys","limit":3,"detail":"compact"}'
```
→ resolves BaseModelSqlv2 call site + client methods.

## Verdict
**Adopt.** Caller-side joint-admission + transaction-scoped factory is the reusable shape for any batch fast-path.
