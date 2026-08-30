<!-- capsule-v2 -->
# node:sqlite adapter contract — what must a sqlite driver guarantee before the whole backend's write path works?

**Source:** pi-upstream MIT `main@4af9d21d3b4d`. **Question:** Every SQLite-backend capsule assumes "one transaction, synchronous callbacks, named-or-positional params" — where is that contract actually manufactured, and why are async transaction callbacks forbidden outright?

## A 5-method driver wrapper that enforces synchronous transactions and normalizes node:sqlite quirks
**Path/Symbol:** `packages/session-backends/sqlite-node/src/index.ts:NodeSqliteDatabase.transaction` (:77-94), `NodeSqliteStatement.run` (:23-32), `isNamedParameters` (:6-10), `isAsyncResult` (:12-14), `createNodeSqliteFactory` (:105-111), `wrapNodeSqliteDatabase` (:101-103).
**Signature:** `transaction<T>(fn: () => T): T` (synchronous callback only); `run(...params): {changes: number, lastInsertRowid?: number}`; factory `open(path): Promise<SqliteDatabase>`.
**Data Shape:** the whole backend programs against the `SqliteDatabase`/`SqliteStatement` interfaces (exec/prepare/transaction/close; run/get/all/iterate) — the driver is swappable behind two entry points. Params: first argument that is a non-null, non-array, non-ArrayBuffer-view object ⇒ named binding (`:name`); otherwise positional spread.

### Decisive source
```ts
transaction<T>(fn: () => T): T {
	sql`BEGIN IMMEDIATE`.exec(this);
	try {
		const result = fn();
		if (isAsyncResult(result)) {
			throw new TypeError("SQLite transaction callbacks must be synchronous");
		}
		sql`COMMIT`.exec(this);
		return result;
	} catch (error) {
		try {
			sql`ROLLBACK`.exec(this);
		} catch {
			// Ignore rollback errors to rethrow original error.
		}
		throw error;
	}
}
```

**Flow:** BEGIN IMMEDIATE opens the write transaction (the same statement the fenced-lease write path relies on) → the callback runs synchronously; if it returned a promise, that is a bug caught HERE with a TypeError — but BEGIN already happened, so the catch path ROLLBACKs and the database is left clean with zero partial writes → COMMIT only after a synchronous result; any error (including the async rejection) triggers ROLLBACK, and rollback failures are swallowed so the ORIGINAL error propagates. `run()` normalizes `changes`/`lastInsertRowid` through `Number()` because node:sqlite can hand back bigint.
**Invariant:** the synchronous-only rule is what lets every storage helper (`claimWriterLease`, `insertBranchEntriesForPath`, the fork body, the delete cascade) compose plain function calls inside ONE transaction with no await points — an await inside a transaction would let another process's writer interleave between BEGIN and COMMIT and break the lease-renew-inside-transaction invariant. The adapter converts that architectural constraint into a loud TypeError at the only place transactions are created, instead of a silent correctness bug. Rollback-error swallowing preserves error attribution: the caller sees the failure that CAUSED the rollback, not the rollback's own failure.
**Probe:** `packages/session-backends/sqlite-node/test/adapter.test.ts` (whole file, 57 lines): synchronous transaction commits and returns its result (:5-18); positional AND named params forward correctly, `{changes, lastInsertRowid}` shape pinned (:20-35); `"rejects asynchronous transaction callbacks"` (:37-54 — TypeError thrown, and after `await Promise.resolve()` the table is EMPTY: the rollback already ran, zero rows survive).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-upstream", query: "NodeSqliteDatabase transaction BEGIN IMMEDIATE synchronous callback adapter", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt: wrap the driver behind a minimal interface and enforce synchronous transaction callbacks at the wrapper with BEGIN-first/ROLLBACK-on-any-failure semantics — this is the enabling contract for lease-renew-inside-transaction and every all-or-nothing cascade in the SQLite capsules. Adapt the param dispatch (named-object vs positional) to your driver's binding rules, and keep the bigint→Number normalization if your driver returns bigint counters. Omit the dedicated adapter package if your host runtime has a synchronous sqlite API with the same semantics — but keep the async-callback rejection: it is the guard that makes the whole write path's single-transaction reasoning valid. Coverage caveat: the adapter has its own test file at this pin; no test covers `iterate()` (interface member, unused by the backend's read paths, which all use `all`/`get`).
