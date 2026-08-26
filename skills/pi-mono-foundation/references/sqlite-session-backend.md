<!-- capsule-v2 -->
# SQLite session backend — how does a durable storage backend implement the agent's session contract and prove itself equivalent to the reference backends?

**Source:** pi-mono MIT `main@80e62761f7251a104f1b21d9c73920c720f0ec00`; Codebase Memory `pi-mono`. **Question:** What is the minimal storage-interface contract for a pluggable session backend, and how is a new backend kept behaviorally identical to JSONL/memory?

## Storage interface + serialized write path + conformance battery
**Path/Symbol:** `packages/agent/src/harness/session/types.ts:SessionStorage` (:290-326); `packages/session-backends/sqlite-node/src/sqlite/repo.ts:SqliteSessionStorage.appendEntry` (:456-484); `packages/session-backends/sqlite-node/src/sqlite/storage/branch-entries.ts:copyBranchEntriesThroughSeq` (:163-174); direct test `packages/session-backends/sqlite-node/test/conformance.test.ts`.
**Signature:** `interface SessionStorage { getMetadata(); lanes: getLanes/createLane/moveLane; appendEntry<T>(entry: ProvisionedEntry<T>, lane): Promise<T>; appendRecord; reads: getEntry/findEntries/findEntriesOnBranch({start}!)/findRecords/findOpenOperations(lane,{limit?})/getLog(afterSeq?,limit?); facts: getName/setName/getLabel/setLabel/getStats }`
**Data Shape:** entries form a parent-linked tree (`parentId`, monotonic `seq`, server-stamped `timestamp` assigned at commit); lanes are named leaf pointers; branch caches are derived tables keyed by `(session_id, branch_id, entry_seq)`.

### Decisive source
```ts
async appendEntry<TEntry extends Entry>(entry: ProvisionedEntry<TEntry>, lane: string): Promise<TEntry> {
    return this.enqueueWrite(() => {
        const parentId = readLaneHead(this.db, this.metadata.id, lane).leafId;
        assertUnusedId(this.db, this.metadata.id, entry.id);
        const seq = getNextSequence(this.db, this.metadata.id);
        const committed = { ...entry, parentId, seq, timestamp: Date.now() } as Entry;
        insertEntryRow(...); setLaneLeaf(...); appendEntryToBranchCache(...);
        if (committed.type === "message") incrementMessageCount(this.db, this.metadata.id);
        advanceSequence(this.db, this.metadata.id, seq);
        return structuredClone(committed as TEntry);
    });
}
```

**Flow:** every mutation funnels through a single serialized write queue → lane head supplies parentId → id-uniqueness assert → sequence allocated → entry row + lane-leaf move + derived branch-cache row + stats written together → clone returned so callers can't hold DB-owned objects. Branch forks copy cached rows wholesale via `copyBranchEntriesThroughSeq(target, source, throughSeq)`. Recovery reads use `findOpenOperations` with `limit: 2` (0=idle, 1=suspended, 2+=corruption — documented on the interface).
**Invariant:** parent linkage, seq, and timestamp are storage-assigned inside one queued write — callers may never supply them; `findEntriesOnBranch` requires an explicit `start` (lane-leaf defaulting is explicitly view sugar, per the interface comment).
**Probe:** `packages/session-backends/sqlite-node/test/conformance.test.ts` binds `SqliteSessionRepository` into the shared `createSessionBackendConformance` battery from `@earendil-works/pi-agent-core/session/testing` — the SAME generated suite any backend must pass. Executed GREEN this pass: **30/30 tests passed**.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-mono", query: "sqlite session storage backend persist entries branch sequences", limit: 20 });
// executed live this pass: ranked branch-entries cache plane (#1-#9), repo.appendEntry :456-484;
// trace_path inbound on copyBranchEntriesThroughSeq → appendEntryToBranchCache / SqliteSessionStorage.appendEntry.
```

## Verdict
Adopt the interface shape, write-queue serialization, storage-assigned identity fields, derived branch caches, and above all the shared conformance-battery pattern for your own backends. Adapt SQL specifics to your store. Omit the FTS search-backend plane (separate seam). Coverage caveat: `sqlite-node/src/sqlite/migrations/001_initial.sql` is parse-partial in the graph (SQL ranges flagged) — schema claims here rest on repo.ts reads, not graph output. All other cited paths `no_recorded_issue` at generation 2026-08-24T16:11:21Z.
