<!-- capsule-v2 -->
# Session backend conformance harness — how do you make a storage contract executable so every backend (memory, JSONL, SQLite, server) proves the same behavior?

**Source:** pi-upstream MIT `main@4af9d21d3b4d`; Codebase Memory `pi-upstream`. **Question:** How do you stop three storage implementations from drifting apart when each has a completely different persistence mechanism?

## One factory of test cases; each backend ships a 50-line adapter running them all
**Path/Symbol:** `packages/agent/src/harness/session/testing/conformance.ts:createSessionBackendConformance` (:92–1016) consumed by `packages/session-backends/sqlite-node/test/conformance.test.ts:24-54`.
**Signature:** `createSessionBackendConformance(factory: SessionBackendFixtureFactory): readonly SessionBackendConformanceCase[]` where a case = `{ group, name, run() }` and `run` creates + disposes its own fixture via `await using`.
**Data Shape:** fixture adapts a concrete repo to the generic `SessionRepo` surface (`create/open/list/delete/fork`); SQLite's adapter widens metadata (`cwd`, `path`) and defaults `cwd` into options.

### Decisive source
```ts
const conformance = createSessionBackendConformance(async () => {
	const root = createTempDir();
	const sqliteRepository = new SqliteSessionRepository({ env: …, sqlite: createNodeSqliteFactory(), databasePath: join(root, "sessions.sqlite") });
	const repository: SessionRepo = {
		create: (options = {}) => sqliteRepository.create({ ...options, cwd: root }),
		open: (metadata) => sqliteRepository.open(requireSqliteMetadata(metadata)),
		list: () => sqliteRepository.list(),
		delete: (metadata) => sqliteRepository.delete(requireSqliteMetadata(metadata)),
		fork: (source, options = {}) => sqliteRepository.fork(requireSqliteMetadata(source), { ...options, cwd: root }),
	};
	return { repository, async [Symbol.asyncDispose]() { await sqliteRepository.close(); } } satisfies SessionBackendFixture;
});

describe("SqliteSessionRepository conformance", () => {
	for (const group of new Set(conformance.map((testCase) => testCase.group))) {
		describe(group, () => {
			for (const testCase of conformance.filter((candidate) => candidate.group === group)) it(testCase.name, () => testCase.run());
		});
	}
});
```

**Flow:** the factory returns **30 cases in 6 groups**, each asserting cross-backend behavior via error-code contracts (`rejectsWithCode(promise, "not_found" | "already_exists" | "invalid_entry" | "invalid_query" | "invalid_fork_target" | …)`), never message matching:
- **entries and lanes (8)** — parents + one sequence across every mutation kind (seqs 1..7 merged through `getLog`: entry/lane/entry/record/fact/fact/lane-move); duplicate ids rejected without state change; lanes share one tree; lane lifecycle/target validation; lane views bind without caching leaves; provisioned entries keep their ids; tool-result termination decisions persist; concurrent writes across two lanes linearize.
- **records and log (8)** — :146 "commits records and lane moves as separate mutations"; :310 "keeps lane names permanent with their recovery records"; :338 "persists queue cancellation without consuming its target"; :370 "filters records by lane type run sequence and order"; :415 "filters operation starts by operation kind"; :483 "tracks and enforces one open operation per lane"; :505 "does not let an earlier finish close a later start"; :523 "scopes open operations by lane and limit". The three open-operation cases are the cross-backend witness for the leaf's admission seam, quoted verbatim:

```ts
createCase(factory, "records and log", "tracks and enforces one open operation per lane", async (repository) => {
	const session = await repository.create({ id: "session" });
	deepStrictEqual(await session.findOpenOperations("main", { limit: 2 }), []);
	const first = await session.appendRecord(operationStarted("first", { lane: "main", kind: "run" }));
	deepStrictEqual(await session.findOpenOperations("main", { limit: 2 }), [first]);
	await rejectsWithCode(session.appendRecord(operationStarted("second", { lane: "main", kind: "run" })), "storage");
	deepStrictEqual(await session.findOpenOperations("main", { limit: 2 }), [first]);
	await session.appendRecord({ type: "operation_finished", id: "finish-first", lane: "main", runId: first.id, outcome: "completed" });
	deepStrictEqual(await session.findOpenOperations("main", { limit: 2 }), []);
}),
createCase(factory, "records and log", "does not let an earlier finish close a later start", async (repository) => {
	const session = await repository.create({ id: "session" });
	await session.appendRecord({ type: "operation_finished", id: "finish-before-start", lane: "main", runId: "run", outcome: "completed" });
	const started = await session.appendRecord(operationStarted("run", { lane: "main", kind: "run" }));
	deepStrictEqual(await session.findOpenOperations("main", { limit: 2 }), [started]);
}),
```

The enforcement case runs the contract docstring's own probe shape (`limit: 2`) against every backend fixture: [] before start, [first] after, second start rejects with code `storage` leaving state unchanged, [] after finish. The orphaned-finish case appends a finish BEFORE any start: it is accepted (finishes are records, not claims) and the later start with that runId still reports open — an index backend implements this as `delete(runId)` on a missing key, the SQLite backend as a zero-row `UPDATE … WHERE open_operation_id = runId`; both no-ops. The scoping case (:523) pins per-lane isolation plus limit behavior.
- **queries and facts (4)** — invalid queries rejected BEFORE empty reads (limit 0/-1, negative cursors ⇒ `invalid_query`); bounded filtered + cursor-based queries including direction-dependent stop-boundary windows; latest-value facts + ledger statistics across lanes; session name cleared durably.
- **validation and immutability (4)** — open-operation records returned immutable; all reads return immutable copies; non-JSON entries AND records rejected before any storage mutation.
- **repository and forks (6)** — create/list/open round-trip with `already_exists`; delete idempotent (second delete resolves, open after delete rejects `not_found`); branch-scope fork copies only the target branch prefix, carries the name fact + labels filtered to copied ids, copies NO records, recomputes stats from copied entries (messageCount 3, tokens/cost 0), sets `parentSessionId`; tree-scope fork copies all lanes with fresh seqs (lane mutations at seq 4,5); `position` defaults to "before" when `entryId` is given and "at" when it is not; non-message default fork target rejects `invalid_fork_target`.

Each consumer (memory/jsonl/sqlite/server test files) just binds its own fixture; `await using` disposes per case so cases are hermetic.
**Invariant:** the CONTRACT lives in one place; backends differ only in their fixture. A new storage implementation is "done" when this unknown set of shared cases passes — not when its own bespoke tests pass. Error taxonomy (`SessionErrorCode`) doubles as the portability boundary for callers.
**Probe:** the harness itself IS the probe generator; deterministic check executed this pass: `packages/agent/test/harness/session/{memory,jsonl}` + `packages/server/test/conformance.test.ts` exist as sibling consumers (graph-verified pass 4), proving multi-backend reuse rather than a single-consumer helper. Full 30-case/6-group inventory above was read directly from :92–1016 (fork-group assertions quoted verbatim from the source); pass 6 deep-read the records-and-log group (:146–534) and quoted its open-operation cases verbatim above.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-upstream", name_pattern: ".*createSessionBackendConformance.*", limit: 10 });
```

## Verdict
Adopt the pattern for any multi-backend subsystem you port: export case factories from the core package, keep fixtures tiny, assert error codes not messages. Adapt grouping/naming to your runner. Omit nothing structural — the value collapses if even one backend keeps private tests for shared behavior. When porting a second backend, port the WHOLE group set in one go: the fork group alone pins five behaviors (scope semantics, fact/label filtering, record exclusion, stats recomputation, position defaults) that are easy to get half-right. Caveat: MCP graph was not connected this pass; anchors verified by direct read at pin `4af9d21d`.
