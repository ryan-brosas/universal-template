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

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.get_code_snippet({ project: "pi-upstream", qualified_name: "pi-upstream.packages.session-backends.sqlite-node.src.sqlite.repo.SqliteSessionRepository.fork" });
```

## Verdict
Adopt: id-stable/seq-fresh copying, message-target validation with at/before→parent resolution, label filtering to copied ids, derived-state recomputation inside one transaction ending with the lease claim. Adapt scope names and lane synthesis to your domain. Omit cross-session foreign keys — provenance rides `parent_session_id` metadata only.
