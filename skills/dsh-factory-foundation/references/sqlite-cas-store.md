<!-- capsule-v2 -->
# SQLite CAS store — how does a single-file store give multi-process compare-and-set with lease-guarded writes?

**Source:** dsh-factory MIT `main@3405edc7`; Codebase Memory `mnt-hdd-utopia-inspo-external-ext-dsh-factory`. **Question:** How do I implement the durable document store so concurrent processes can't clobber each other and a deposed leader can't write?

## SqliteFactoryStore.mutate
**Path/Symbol:** `packages/store-sqlite/src/index.ts` (`SqliteFactoryStore.mutate`, `acquireLeader`, `FactoryRevisionConflictError`, `FactoryLeaderLeaseError`) (:79–156).
**Signature:** `mutate(expectedRevision: number | undefined, mutation: FactoryStoreMutation, lease?: FactoryStoreLeaseGuard): Promise<FactoryStoreRead>`.
**Data Shape:** one row `factory_state(singleton=1, revision, document JSON)`; presence rows keyed `(process_id, agent_id)`; leader row `singleton=1`; PRAGMAs `journal_mode=WAL, foreign_keys=ON, busy_timeout=5000`; `user_version` migration gate (newer schema → hard error).

### Decisive source
```ts
this.database.exec('BEGIN IMMEDIATE')
try {
    if (lease !== undefined) {
      const leader = this.database.prepare('SELECT process_id, expires_at FROM factory_scheduler_leader WHERE singleton = 1').get() ...
      if (leader === undefined || leader.process_id !== lease.processId || leader.expires_at <= lease.now)
        throw new FactoryLeaderLeaseError()
    }
    const current = this.readCurrent()
    if (expectedRevision !== undefined && current.revision !== expectedRevision)
      throw new FactoryRevisionConflictError(expectedRevision, current.revision)
    const draft = structuredClone(current.document)
    if (mutation(draft) === FACTORY_STORE_NO_CHANGE) { this.database.exec('ROLLBACK'); return current }
    const issues = validateTaskGraph(draft)
    if (issues.length > 0) throw new Error(`Factory graph rejected: ${issues.map(i => i.message).join('; ')}`)
    const document = parseFactoryDocument(draft)          // zod .strict() — unknown fields rejected
    ... UPDATE factory_state SET revision = revision+1 ...
```

**Flow:** BEGIN IMMEDIATE (write lock up front) → optional LEASE re-check inside the transaction → revision compare-and-set → mutate a structuredClone of the document → NO-CHANGE sentinel rolls back without bumping → graph validation on the draft → strict schema parse → commit with revision+1 → `factory-store/committed` parallel event. Leader election is a timestamped singleton row: acquire succeeds if absent/expired/own; losers get the CURRENT leader back.
**Invariant:** The lease check happens INSIDE the same immediate transaction as the write — acquiring leadership in a separate call and trusting it later would let a deposed leader corrupt state. Validation-before-parse means semantically invalid graphs NEVER reach disk even though parsing alone would accept them; every read returns a fresh structuredClone (callers can't mutate shared state). Failed migrations refuse to open rather than guessing.
**Probe:** `packages/store-sqlite/tests/store.spec.ts` — "commits revisions across processes and rejects stale writers" (`FactoryRevisionConflictError`; stale writer's value NOT applied), "rolls back an invalid graph without advancing the revision", "elects one leader and permits takeover only after expiry". Deterministic from repo root: `grep -c 'validateTaskGraph(draft)' packages/store-sqlite/src/index.ts` = 1.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-external-ext-dsh-factory", query: "SqliteFactoryStore", limit: 5, fields: ["signature", "name", "file"] });
```
(CLI equivalent verified via sibling name-pattern queries on this project.)

## Verdict
Adopt transaction-scoped lease guard + CAS revision + validate-then-parse + NO-CHANGE sentinel + clone-on-read. Adapt SQL dialect/provider freely — the CONTRACT is the sequence. Omit node:sqlite specifics if host has another embedded DB.
