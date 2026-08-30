<!-- capsule-v2 -->
# Session delete cascade — how do you tear down an aggregate that owns derived tables, counters, and a lease row, idempotently?

**Source:** pi-upstream MIT `main@4af9d21d3b4d`. **Question:** How does a SQL session repository delete a session whose state is spread across nine tables — including a writer lease and a sequence counter — so a second delete is a no-op and a live writer can never be deleted underneath?

## One lease-claimed transaction, children before the sessions row; missing session short-circuits to lease cleanup only
**Path/Symbol:** `packages/session-backends/sqlite-node/src/sqlite/repo.ts:SqliteSessionRepository.delete` (:774-794); helpers `deleteBranchCache` (`branch-cache.ts:14-17`), `deleteFactRows` (`storage/facts.ts:62`), `deleteLaneRows` (`storage/lanes.ts:115`), `deleteRecordRows` (`storage/records.ts:42`), `deleteEntryRows` (`storage/entries.ts:76`), `deleteWriterLease` (`storage/writer-leases.ts:56`), `deleteStats` (`storage/session-stats.ts:52`), `deleteSequence` (`storage/session-sequences.ts:27`), `deleteSessionRow` (`storage/sessions.ts:97`).
**Signature:** `delete(metadata: SqliteSessionMetadata): Promise<void>` — enqueued on the repository serial queue.
**Data Shape:** nine owned tables per session: `branch_tips`, `branch_entries`, `facts`, `lanes`, `records`, `entries`, `writer_leases`, `session_stats`, `session_sequences`, plus the `sessions` row itself. Every helper is a single unconditional `DELETE FROM <table> WHERE session_id = ?` — zero rows affected is a valid outcome, never an error.

### Decisive source
```ts
async delete(metadata: SqliteSessionMetadata): Promise<void> {
	return this.operations.enqueue(async () => {
		await this.releaseStoragesForSession(metadata.id);
		const db = await this.getDatabase();
		db.transaction(() => {
			if (!sessionExists(db, metadata.id)) {
				deleteWriterLease(db, metadata.id);
				return;
			}
			claimWriterLease(db, metadata.id, this.leaseOptions);
			deleteBranchCache(db, metadata.id);
			deleteFactRows(db, metadata.id);
			deleteLaneRows(db, metadata.id);
			deleteRecordRows(db, metadata.id);
			deleteEntryRows(db, metadata.id);
			deleteWriterLease(db, metadata.id);
			deleteStats(db, metadata.id);
			deleteSequence(db, metadata.id);
			deleteSessionRow(db, metadata.id);
		});
	});
}
```

**Flow:** active storages for the session are released FIRST (their leases must be free, not stolen) → one transaction: if the session row is already gone, ONLY the stale writer lease is cleared and the transaction ends (idempotence arm) → otherwise the lease is claimed (so a concurrent writer in another process fails its renew and cannot interleave), then all nine child tables are cleared children-before-parent, ending with the `sessions` row as the tombstone → the lease is DELETED, not released: the fence row must not survive the aggregate, and a later `create` with a recycled id must start with a clean lease state.
**Invariant:** delete is all-or-nothing (single transaction ⇒ crash leaves either the full aggregate or none of it) and idempotent by structure — the second call takes the `!sessionExists` arm and still succeeds; the conformance case "deletes sessions idempotently" (`packages/agent/src/harness/session/testing/conformance.ts:882-889`) pins exactly this: delete → `open` rejects `not_found` → second delete resolves. Ordering within the transaction is not load-bearing for correctness (SQLite atomicity covers it), but ending on `deleteSessionRow` makes the sessions row the single existence marker every other path (`requireSessionRow`, `sessionExists`) already checks.
**Probe:** `packages/agent/src/harness/session/testing/conformance.ts:882-889` (idempotence + not_found, every backend fixture); deterministic node:sqlite probe P1 this pass (verification.md): after `delete`, all nine tables return zero rows for the id and a second delete returns cleanly.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-upstream", name_pattern: ".*(deleteWriterLease|deleteSessionRow|deleteBranchCache)", limit: 10 });
```

## Verdict
Adopt: cascade-delete inside one lease-claimed transaction, unconditional per-table deletes, missing-aggregate short-circuit that still cleans the lease, aggregate row deleted last as the existence marker. Adapt the table list to your schema. Omit soft-delete/tombstone columns here — the append-only streams (entries/records/facts) are the history, and delete means delete. Caveat: delete does NOT remove FTS rows directly — they follow `entries` via the external-content triggers; a backend without trigger parity must add its own search-index cleanup.
