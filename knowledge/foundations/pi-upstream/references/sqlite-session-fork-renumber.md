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

## Fact selection: latest name + latest labels filtered to copied keys, read from the SOURCE before the txn
**Path/Symbol:** `repo.ts:SqliteSessionRepository.fork` fact-selection block (:846-851 read side, :878-884 write side).
**Signature:** `readLatestFact(db, source.id, "name", null)` + `readLatestLabelFacts(db, source.id)` evaluated OUTSIDE the write transaction; filter `labelsToCopy = latestLabels.filter(row => options.scope === "tree" || (row.key !== null && copiedIds.has(row.key)))` where `copiedIds = new Set(entries.map(e => e.id))`.
**Data Shape:** facts copy as fresh appends into the child's log (`appendFact(db, id, allocateSeq(), "name", null, value)` / `("label", label.key, label.value)`) — the child gets its own fact history starting at the copied latest values, not a copy of the source's fact log.

### Decisive source
```ts
const copiedIds = new Set(entries.map((entry) => entry.id));
const latestName = readLatestFact(db, source.id, "name", null);
const latestLabels = readLatestLabelFacts(db, source.id);
const labelsToCopy = latestLabels.filter(
	(row) => options.scope === "tree" || (row.key !== null && copiedIds.has(row.key)),
);
...
if (latestName?.value !== undefined && latestName.value !== null) {
	appendFact(db, id, allocateSeq(), "name", null, latestName.value);
}
for (const label of labelsToCopy) appendFact(db, id, allocateSeq(), "label", label.key, label.value);
```

**Flow:** the name fact ALWAYS copies when set (its key is `null`, so the branch-scope filter never drops it) and copies nothing when undefined (never set) or null (cleared — the guard is `!== undefined && !== null`). Labels copy per-key: a label on a copied entry rides the fork; a label on an excluded entry does not. Tree scope copies ALL latest labels regardless of key. Records copy NEVER — `findRecords()` is `[]` on a fresh fork (operational history is not state). Stats are recomputed from copied entries only: conformance "forks one branch with selected facts and no records" (:893-950) pins `getStats()` = `{messageCount: 3, cachedTokens: 0, uncachedTokens: 0, totalTokens: 0, costTotal: 0}` — the source's usage record does NOT ride along — and the fork is immediately writable (appendMessage bumps messageCount 3→4).
**Invariant:** a fork carries STATE (name, labels-on-copied-entries, entry graph, lane structure) and drops HISTORY (records, usage, fact revision log). The latest-value read happens against the SOURCE before the transaction, so the copied values are a consistent snapshot; the child's fact log restarts at those values with fresh seqs.
**Probe:** deterministic probe P1 this pass (verification.md) — transcribed the filter on the conformance fixture shape: name (key null) survives branch scope; label on copied id survives; label on excluded id drops; tree scope keeps both labels.

## Tree-scope arm: lanes copy as lane-log mutations AFTER entries; the cache is rebuilt per tip, never inherited
**Path/Symbol:** `repo.ts:SqliteSessionRepository.fork` tree arm (:813–817 read side, :880–884 write side); helpers `readLanes` (storage/lanes.ts:24–41), `readBranchTipIds` (storage/branch-tips.ts:4–7), `createInitialLane` (lanes.ts:19–24), `buildCachedBranch` (storage/branch-cache.ts:31–37).
**Signature:** `fork(source, { scope: "tree", id })` — no `entryId`/`position` resolution, no message-target validation.
**Data Shape:** tree reads ALL entries oldestFirst, ALL lanes, and ALL branch tip ids (`SELECT tip_id FROM branch_tips … ORDER BY tip_id`) OUTSIDE the txn; branch arm instead synthesizes ONE `main` lane via a plain INSERT with `open_operation_id = NULL`.

### Decisive source
```ts
// read side (:813-817)
entries.push(...readEntryRows(db, source.id, { order: "oldestFirst" }));
lanes.push(...readLanes(db, source.id).map((row) => ({ lane: row.lane, leafId: row.leaf_id })));
branchTips.push(...readBranchTipIds(db, source.id));
// write side (:880-884), AFTER the entry copy loop consumed seqs 1..n
if (options.scope === "tree") {
	for (const lane of lanes) insertLane(db, id, allocateSeq(), lane.lane, lane.leafId);
} else {
	createInitialLane(db, id, "main", branchForkTargetId);
}
...
for (const tip of branchTips) buildCachedBranch(db, id, tip);
```

**Flow:** `readLanes` on the SOURCE re-proves leaf referential integrity before any copy (its EXISTS-subquery check throws "Lane X points at missing entry Y" — the twin-pointer rule), so a tampered source cannot fork. Inside the single transaction the lane copy consumes its own sequence numbers AFTER the entries: a 3-entry tree gives lanes seqs 4 and 5, exactly what the conformance case "forks a complete tree with lanes and facts" (:951–977) pins — `getLog()` lane items `[{seq: 4, lane: "main", leafId: mainChild}, {seq: 5, lane: "thread", leafId: threadChild}]`, both leafIds preserved. The branch cache is then rebuilt per tip (`buildCachedBranch` walks canonical parents under a SAVEPOINT, fresh uuidv7 branch ids) — cache rows are DERIVED from the copied entries, never copied, so the child's cache cannot inherit source drift.
**Invariant:** lanes are lane-log mutations with fresh seqs, not copied rows with source seqs — the child's merged log stays a dense 1..n total order across entries, lanes, and facts. Branch arm vs tree arm differ ONLY in what they read and which lane-insert helper runs; the transaction shape, fact selection, and per-tip rebuild are shared.
**Probe:** deterministic probe P1 this pass (verification.md) — transcribed the tree-arm write order on a 3-entry/2-lane fixture: lane inserts land at seq 4,5 with preserved leafIds; per-tip rebuild derives fresh branch ids.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.get_code_snippet({ project: "pi-upstream", qualified_name: "pi-upstream.packages.session-backends.sqlite-node.src.sqlite.repo.SqliteSessionRepository.fork" });
```

## Verdict
Adopt: id-stable/seq-fresh copying, message-target validation with at/before→parent resolution, label filtering to copied ids, derived-state recomputation inside one transaction ending with the lease claim — the transaction boundary is load-bearing: repository.test.ts proves a mid-copy abort leaves zero rows for the fork id. Adopt the fact-selection split too: state rides (latest name always; labels filtered to copied keys; tree scope unfiltered), history drops (records, usage, fact revisions), and the child's fact log restarts at the snapshot values. Adapt scope names and lane synthesis to your domain. Omit cross-session foreign keys — provenance rides `parent_session_id` metadata only.
