<!-- capsule-v2 -->
# Fenced writer lease — how does a SQLite session storage grant exactly one cross-process writer and take over safely after a crash?

**Source:** pi-upstream MIT `main@4af9d21d3b4d`; Codebase Memory `pi-upstream`. **Question:** When two processes open the same sessions database, who may write a session, how is an expired owner evicted, and why can an evicted owner never write again?

## Lease row + conditional-upsert acquire
**Path/Symbol:** `packages/session-backends/sqlite-node/src/sqlite/storage/writer-leases.ts:acquireWriterLease` (:16–32); schema comment in `migrations/001_initial.sql:115-122`.
**Signature:** `acquireWriterLease(db, sessionId, ownerId, now, expiresAtMs): WriterLease | undefined` where `WriterLease = { ownerId, fence, expiresAtMs }`.
**Data Shape:** one `writer_leases` row per session (`session_id` PK, `owner_id`, monotone `fence`, absolute `expires_at_ms`). Acquire returns a lease only when no live lease existed; `undefined` means "someone else holds it".

### Decisive source
```sql
INSERT INTO writer_leases (session_id, owner_id, fence, expires_at_ms)
	VALUES (${sessionId}, ${ownerId}, 1, ${expiresAtMs})
	ON CONFLICT(session_id) DO UPDATE SET
		owner_id = excluded.owner_id,
		fence = writer_leases.fence + 1,
		expires_at_ms = excluded.expires_at_ms
	WHERE writer_leases.expires_at_ms <= ${now}
	RETURNING owner_id, fence, expires_at_ms
```

**Flow:** insert-or-steal in ONE statement → steal permitted only when the stored expiry has passed (`expires_at_ms <= now`) → every takeover increments `fence`, so ownership generations are totally ordered → `RETURNING` yields the row on success and nothing when the WHERE filtered the update out (live lease) → caller maps `undefined` to `SessionError("storage", "... already has an active writer")`.
**Invariant:** an expired owner can never silently coexist with a new one: the new owner's write path re-checks `fence` (see renew), so post-takeover writes by the old generation fail. Renewal (`renewWriterLease`, :34–49) requires `owner_id AND fence AND expires_at_ms > now` in one UPDATE; release (:51–54) deletes only where `owner_id AND fence` still match — a stale owner closing late cannot delete the new owner's lease.
**Probe:** `packages/session-backends/sqlite-node/test/writer-leases.test.ts:127-173` — expire via raw SQL `UPDATE … SET expires_at_ms = 0`, second repo takes over, assert `fence === 2`, stale owner's append rejects "writer lease was lost", stale repo's later `close()` leaves the new lease byte-identical.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-upstream", name_pattern: ".*WriterLease.*", limit: 10 });
```

## Verdict
Adopt the fenced-lease shape verbatim: conditional upsert stealing expired-only + RETURNING, fence bump per takeover, renew/release guarded by owner+fence. Adapt TTL/heartbeat defaults (30s/10s here, validated positive with heartbeat < ttl in `repo.ts:114-122`) to your host's failure detector. Omit nothing from the WHERE clauses — dropping the fence or the expired-only steal reintroduces split-brain writes.
