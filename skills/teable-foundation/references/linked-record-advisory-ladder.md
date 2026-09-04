<!-- capsule-v2 -->
# Linked-record advisory lock ladder — how do concurrent link mutations avoid deadlocks on foreign rows?

## dedupe → SORT keys → one unnest query of pg_advisory_xact_lock(md5→bit64), ordered
**Path/Symbol:** `PostgresTableRecordRepository.ts` — `buildLinkedRecordLockKey` (:4562–4566, format `` `v2:link:${baseId}:${foreignTableId}:${foreignRecordId}` ``), `acquireLinkedRecordLocks(db, baseId, locks)` (:4573–4600, SQL :4595–4599); call sites after DML in insert :1292–1294 / insertMany :1683–1685 / updateOne :2175–2177 / updateManyStream :2736–2738. Companion capsule: `computed-update-lock-ladder`.
**Signature:** `(db, baseId: string, linkedRecordLocks: LinkedRecordLockInfo[]): Promise<void>`.

### Decisive source
```ts
const lockKeys = [...lockKeysSet].sort();          // consistent ordering across transactions
const arrayLiteral = `ARRAY[${lockKeys.map(k => `'${k.replace(/'/g,"''")}'`).join(',')}]`;
await db.executeQuery(sql`
  SELECT pg_advisory_xact_lock(('x' || substr(md5(k),1,16))::bit(64)::bigint)
  FROM unnest(${sql.raw(arrayLiteral)}::text[]) AS k
  ORDER BY k`.compile(db));
```

**Flow:** collect foreign (tableId, recordId) pairs the mutation touches → dedupe into namespaced string keys → sort lexically → take all session-scoped... rather transaction-scoped advisory locks in ONE statement that walks the array in sorted order.
**Invariant:** FOUR facts porters get wrong: (1) Locks are acquired AFTER the core DML but BEFORE junction/additional statements — the primary row write already holds its own tuple locks; the advisory set protects CROSS-TABLE orderings that tuple locks cannot express. (2) `ORDER BY k` inside SQL plus pre-sorted input is what prevents the ABBA deadlock between two transactions linking overlapping record sets in different orders. (3) The key is md5-hashed to bit(64) because pg_advisory locks want an integer — collisions are astronomically unlikely and only cause false sharing, never missed locks. (4) `pg_advisory_xact_lock` releases automatically at commit/rollback — no unlock path exists or is needed; using the session variant would leak.
**Probe:** update.spec.ts 'acquires advisory lock for oneOne link in updateManyStream' (:1605).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "acquireLinkedRecordLocks pg_advisory_xact_lock buildLinkedRecordLockKey", limit: 5 });
```
## Verdict
Adopt for any multi-row cross-table mutation: sorted, deduped, single-statement transaction-scoped advisory locking over a stable string-key grammar.
