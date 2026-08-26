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

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.get_code_snippet({ project: "pi-upstream", qualified_name: "pi-upstream.packages.session-backends.sqlite-node.src.sqlite.repo.SqliteSessionStorage.enqueueWrite" });
```

## Verdict
Adopt renew-before-commit inside the write transaction and the sticky lost-lease poison (fail fast forever after eviction — do not attempt transparent reacquire). Adapt the serial-queue to your host's concurrency primitive; keep the property that its stored tail ignores errors. Omit node-specifics (`.unref()`) where irrelevant. Caveat: behavioral evidence here is upstream vitest source + deterministic SQL probes; the repo's own runner could not execute this pass (no node_modules — recorded block).
