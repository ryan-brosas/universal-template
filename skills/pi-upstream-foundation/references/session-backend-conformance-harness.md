<!-- capsule-v2 -->
# Session backend conformance harness — how do you make a storage contract executable so every backend (memory, JSONL, SQLite, server) proves the same behavior?

**Source:** pi-upstream MIT `main@4af9d21d3b4d`; Codebase Memory `pi-upstream`. **Question:** How do you stop three storage implementations from drifting apart when each has a completely different persistence mechanism?

## One factory of test cases; each backend ships a 50-line adapter running them all
**Path/Symbol:** `packages/agent/src/harness/session/testing/conformance.ts:createSessionBackendConformance` (:92–1016) consumed by `packages/session-backends/sqlite-node/test/conformance.test.ts:24-54`.
**Signature:** `createSessionBackendConformance(factory: SessionBackendFixtureFactory): readonly SessionBackendConformanceCase[]` where a case = `{ group, name, run() }` and `run` creates + disposes its own fixture.
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

**Flow:** harness returns grouped cases asserting cross-backend behavior — error-code contracts via `rejectsWithCode(promise, "not_found" | "already_exists" | "invalid_entry" | …)`, seq/parent assignment across every mutation kind, log replay order, fork semantics, delete idempotence — and each consumer (memory/jsonl/sqlite/server test files) just binds its own fixture; `await using` disposes per case so cases are hermetic.
**Invariant:** the CONTRACT lives in one place; backends differ only in their fixture. A new storage implementation is "done" when an unknown set of shared cases passes — not when its own bespoke tests pass. Error taxonomy (`SessionErrorCode`) doubles as the portability boundary for callers.
**Probe:** the harness itself IS the probe generator; deterministic check executed this pass: `packages/agent/test/harness/session/{memory,jsonl}` + `packages/server/test/conformance.test.ts` exist as sibling consumers (graph-verified), proving multi-backend reuse rather than a single-consumer helper.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-upstream", name_pattern: ".*createSessionBackendConformance.*", limit: 10 });
```

## Verdict
Adopt the pattern for any multi-backend subsystem you port: export case factories from the core package, keep fixtures tiny, assert error codes not messages. Adapt grouping/naming to your runner. Omit nothing structural — the value collapses if even one backend keeps private tests for shared behavior. Caveat: only case #1 read in full this pass (:96–142); remaining groups are inventoried as next-pass targets.
