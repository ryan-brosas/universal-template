<!-- capsule-v2 -->
# Transactional write ownership — how does every single write re-prove lease ownership, and what happens to a writer the moment it loses the lease?

**Source:** pi-upstream MIT `main@4af9d21d3b4d`; Codebase Memory `pi-upstream`. **Question:** Where in the write path is ownership enforced so a network-paused or SIGSTOP'd writer cannot commit even one mutation after its lease is taken?

## enqueueWrite: serial queue → BEGIN IMMEDIATE → renew-inside-transaction → operation
**Path/Symbol:** `packages/session-backends/sqlite-node/src/sqlite/repo.ts:SqliteSessionStorage.enqueueWrite` (:377–392) with `scheduleHeartbeat` (:394–415), `SerialOperationQueue` (:139–154), `finishRelease` (:365–375).
**Signature:** `enqueueWrite<T>(operation: () => T): Promise<T>`; all mutating SessionStorage methods funnel through it.
**Data Shape:** private state: `operations` promise queue, `heartbeatTimer`, `leaseError` (sticky), `closing` flag, memoized `releasePromise`.

### Decisive source
```ts
return this.operations.enqueue(() => {
	if (this.leaseError) throw this.leaseError;
	return this.db.transaction(() => {
		const now = Date.now();
		if (!renewWriterLease(this.db, this.metadata.id, this.lease, now, now + this.leaseOptions.ttlMs)) {
			this.leaseError = lostWriterError(this.metadata.id);
			if (this.heartbeatTimer !== undefined) clearTimeout(this.heartbeatTimer);
			throw this.leaseError;
		}
		return operation();
	});
});
```

**Flow:** op enqueued on an in-process promise-tail chain (`tail.then(op)`; stored tail swallows results/errors so one rejection never breaks later ops) → `BEGIN IMMEDIATE` grabs the write lock → renew lease with owner+fence+unexpired check INSIDE the same transaction as the mutation → renewal failure permanently sets `leaseError`, clears the heartbeat timer, and aborts the txn; every subsequent write rejects with "writer lease was lost" without touching disk → close path clears the timer first, then enqueues `releaseWriterLease` as a final transaction, exactly once via `releasePromise ??=`.
**Invariant:** ownership is verified by the same transaction that commits the data — there is no window where a check-then-write straddles two transactions. The 10s heartbeat (`setTimeout` with `.unref()`, transient failures retried silently) only keeps the TTL fresh while idle; it is never the correctness mechanism.
**Probe:** `packages/session-backends/sqlite-node/test/writer-leases.test.ts:190-216` — fake timers advance 10s and the stored `expires_at_ms` grows by exactly 10_000; plus :127-173 where the stale writer's next append after takeover rejects with "writer lease was lost" (the sticky-poison behavior).

## Failure classes: an aborted operation is NOT a lost lease
**Path/Symbol:** witness `test/repository.test.ts` "does not publish connection state when an append transaction fails" (:379–409); mechanism `repo.ts:getDatabase` memoization (:931–935) with `close()` as the only clearer (:916).
**Signature:** same `enqueueWrite`; failure shape = the raw operation error, rethrown by the transaction wrapper.

### Decisive source
```ts
// repository.test.ts:388-409 — abort the branch_tips insert mid-append
CREATE TRIGGER fail_branch_tip_insert BEFORE INSERT ON branch_tips
BEGIN SELECT RAISE(ABORT, 'branch insert failed'); END;
await expect(session.appendMessage(createUserMessage("root"))).rejects.toThrow("branch insert failed");
// zero partial state:
expect(lane?.leaf_id).toBeNull();
expect(await db.prepare("SELECT id FROM entries WHERE session_id = ?").all("session-1")).toEqual([]);
expect(await session.getStats()).toMatchObject({ messageCount: 0 });
await db.exec("DROP TRIGGER fail_branch_tip_insert");
// SAME instance, SAME connection: the next append succeeds
const entryId = await session.appendMessage(createUserMessage("root"));
expect(await session.getStats()).toMatchObject({ messageCount: 1 });
```

**Flow:** trigger aborts the branch_tips insert inside the append's lease-renewed transaction → ROLLBACK preserves the original error → lane leaf stays NULL, no entries, stats untouched → the memoized `databasePromise` is never touched by the failure (only `close()` clears it) → the very next append on the same instance succeeds on the same connection.
**Invariant:** there are exactly two writer failure classes: OPERATION failure (roll back own transaction, keep the connection, instance stays writable) and LEASE-RENEWAL failure (sticky poison, never retry). Porters who close/reopen the connection or re-acquire the lease after an ordinary failed write add a recovery path the design deliberately does not have.
**Probe:** deterministic probe P5 this pass (verification.md): transcribed trigger-abort + rollback + retry in node:sqlite — leaf NULL, entries [], messageCount 0, retry commits on the same handle.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.get_code_snippet({ project: "pi-upstream", qualified_name: "pi-upstream.packages.session-backends.sqlite-node.src.sqlite.repo.SqliteSessionStorage.enqueueWrite" });
```

## Verdict
Adopt renew-before-commit inside the write transaction and the sticky lost-lease poison (fail fast forever after eviction — do not attempt transparent reacquire), keeping the failure-class split explicit: an aborted OPERATION rolls back and leaves the instance writable on the retained connection; only renewal loss poisons. Adapt the serial-queue to your host's concurrency primitive; keep the property that its stored tail ignores errors. Omit node-specifics (`.unref()`) where irrelevant. Caveat: behavioral evidence here is upstream vitest source + deterministic SQL probes; the repo's own runner could not execute this pass (no node_modules — recorded block).
