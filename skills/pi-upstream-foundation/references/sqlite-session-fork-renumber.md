<!-- capsule-v2 -->
# Session fork with sequence renumbering — how do you copy a conversation branch into a new session when seq numbers and parent graphs must stay internally consistent?

**Source:** pi-upstream MIT `main@4af9d21d3b4d`; Codebase Memory `pi-upstream`. **Question:** When forking "at" or "before" a message on main, what exactly is copied, in what order are new sequences allocated, and which derived state must be rebuilt rather than copied?

## Single-transaction fork: copy rows, renumber 1..n, rebuild cache per tip, claim lease inside
**Path/Symbol:** `packages/session-backends/sqlite-node/src/sqlite/repo.ts:SqliteSessionRepository.fork` (:797–909).
**Signature:** `fork(source, options: ForkOptions & SqliteSessionCreateOptions): Promise<Session>` with `scope: "tree" | "branch"` (default branch), `entryId`, `position: "at" | "before"`.
**Data Shape:** reads source rows OUTSIDE the write txn first (entries via cache or full scan, lanes, tips, latest name fact, labels), then performs ALL writes atomically.

### Decisive source
```ts
const target = readEntryRow(db, source.id, selectedEntryId);
if (!target || target.type !== "message") {
	throw new SessionError("invalid_fork_target", `Fork target is not a message entry: ${selectedEntryId}`);
}
const position = options.position ?? (options.entryId === undefined ? "at" : "before");
branchForkTargetId = position === "at" ? target.id : target.parent_id;
...
lease = db.transaction(() => {
	insertSessionRow(db, { id, createdAt, cwd: options.cwd, parentSessionId: options.parentSessionId ?? source.id, metadata });
	createSequence(db, id);
	createStats(db, id, entries.filter((entry) => entry.type === "message").length);
	let nextSeq = 1;
	const allocateSeq = () => nextSeq++;
	for (const entry of entries) insertEntryRow(db, id, { seq: allocateSeq(), id: entry.id, parentId: entry.parent_id, … });
	...
	setNextSequence(db, id, nextSeq);
	for (const tip of branchTips) buildCachedBranch(db, id, tip);
	return claimWriterLease(db, id, this.leaseOptions);
});
```

**Flow:** resolve scope → tree copies every entry + all lanes + all tip ids; branch requires the target be a MESSAGE entry ("at" keeps it as leaf, "before" forks at its PARENT), reads only the cached branch prefix through that point (`invalid_fork_target` if the cache row is missing — pinned by branch-cache.test.ts:143-170), and synthesizes a single `main` lane → collect latest name fact + labels filtered to copied ids (`copiedIds.has(row.key)`) → one transaction inserts the child session row, counter, stats seeded with message count, re-numbered entries (ids preserved, seqs fresh), lanes/facts, sets the counter, REBUILDS cache per tip from canonical parents, claims the lease — the returned session is immediately writable by this process.
**Invariant:** entry IDs are stable across forks but sequence numbers are NOT — they belong to the session's log, so children renumber 1..n and the counter is set once at the end. Everything derived (stats counts, branch cache) is recomputed, never copied.
**Probe:** `packages/session-backends/sqlite-node/test/conformance.test.ts` fork groups run the shared harness cases against this implementation; deterministic probe P6 (verification.md) exercised the "before"-position arithmetic `position === "at" ? target.id : target.parent_id` shape on synthetic rows.

## All-or-nothing: a mid-copy failure leaves no ghost session
**Path/Symbol:** witness `packages/session-backends/sqlite-node/test/repository.test.ts` "rolls back the entire fork when copying an entry fails" (:119–156); mechanism = the single `db.transaction` above.
**Signature:** same `fork(source, options)`; failure shape `{ code: "storage" }`.

### Decisive source
```ts
// repository.test.ts:131-144 — abort the SECOND copied entry inside the fork txn
await db.exec(`
CREATE TRIGGER fail_fork_entry BEFORE INSERT ON entries
WHEN new.session_id = 'fork' AND new.seq = 2
BEGIN
  SELECT RAISE(ABORT, 'fail fork');
END;
`);
await expect(repo.fork(await source.getMetadata(), { cwd: root, id: "fork" })).rejects.toMatchObject({
	code: "storage",
});
// inspection on a FRESH connection (:145-155):
expect(await inspection.prepare("SELECT id FROM sessions WHERE id = ?").get("fork")).toBeUndefined();
expect(await inspection.prepare("SELECT id FROM entries WHERE session_id = ?").all("fork")).toEqual([]);
```

**Flow:** trigger RAISE(ABORT)s on the fork's second entry copy → the whole fork transaction rolls back → fork rejects `{code: "storage"}` → a fresh connection sees NO sessions row and NO entries rows for the fork id. Nothing about the fork is observable until the entire copy commits.
**Invariant:** partial forks are unobservable by construction — session row, counter, stats, entries, lanes, facts, and rebuilt cache rows are all-or-nothing. A porter who inserts the child session row BEFORE the copy loop (to make it listable early) breaks this: a failed copy leaves a ghost session with zero entries.
**Probe:** deterministic probe P1 this pass (verification.md) transcribed trigger + two-step insert + rollback in node:sqlite — sessions row ABSENT, entries [] after rollback.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.get_code_snippet({ project: "pi-upstream", qualified_name: "pi-upstream.packages.session-backends.sqlite-node.src.sqlite.repo.SqliteSessionRepository.fork" });
```

## Verdict
Adopt: id-stable/seq-fresh copying, message-target validation with at/before→parent resolution, label filtering to copied ids, derived-state recomputation inside one transaction ending with the lease claim — the transaction boundary is load-bearing: repository.test.ts proves a mid-copy abort leaves zero rows for the fork id. Adapt scope names and lane synthesis to your domain. Omit cross-session foreign keys — provenance rides `parent_session_id` metadata only.
