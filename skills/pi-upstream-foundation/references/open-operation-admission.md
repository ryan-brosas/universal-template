<!-- capsule-v2 -->
# One-open-operation-per-lane — how is concurrent-operation corruption prevented at write time?

**Source:** pi-upstream MIT `main@a470b121bf683b4c2b9fc0b3a7c807de7e0cfe9c`; Codebase Memory `pi-upstream`. **Question:** Recovery treats ≥2 open operations as corruption — what stops two operations from EVER being open on one lane in the first place?

## Storage-level admission control on operation_started
**Path/Symbol:** `packages/agent/src/harness/session/memory.ts:72-89` (`InMemorySessionStorage.appendRecord`), identical guard `packages/agent/src/harness/session/jsonl/storage.ts:171-192`; open-op index maintained by `SessionState.applyMutation` (`state.ts:132-141`); repo-level race guard `packages/agent/src/harness/session/jsonl/repo.ts:174-188` (`claimCreateDestination`).
**Signature:** `appendRecord(newRecord)` → before staging, `findOpenOperations(lane, {limit:1})[0]?.id`; if starting an operation while one is already open → `throw new SessionError("storage", "Lane <lane> already has an open operation <id>")`.
**Data Shape:** `openOperationsByLane: Map<lane, Map<operationId, OperationStartedRecord>>`; started inserts on apply, finished deletes by `runId`. Repo guard keys on `` `${cwd}\0${id}` `` in `activeCreateDestinations`.

### Decisive source
```ts
const currentOpenOperationId = this.state.findOpenOperations(newRecord.lane, { limit: 1 })[0]?.id;
if (newRecord.type === "operation_started" && currentOpenOperationId !== undefined) {
    throw new SessionError(
        "storage",
        `Lane ${newRecord.lane} already has an open operation ${currentOpenOperationId}`,
    );
}
```

**Flow:** appendRecord → lane must exist → id must be unused → admission check (open op?) → stage `{...clone(newRecord), seq, timestamp}` → persist (JSONL) then apply. Because the check and the index update happen inside the same serialized path (inline for memory; the promise-tail queue for JSONL), no interleaving can admit a second start. Separately, `claimCreateDestination` prevents same-process create/fork races on one destination: timestamped filenames make async existence checks unreliable, so concurrent creates of the same `{cwd,id}` throw `already_exists`.
**Invariant:** The recovery tri-state (0 idle / 1 suspended / 2+ corrupt) is only decidable because writers make "2+" unreachable except through external corruption; the enforcement lives in BOTH backends identically — it is part of the storage contract, not the agent loop's discipline. Note the asymmetry: the durable filename embeds creation timestamp + id (`${toISOString}_${id}.jsonl`), so existence-check races are closed by the in-process claim set, not by the filesystem.
**Probe:** `packages/agent/test/harness/session/jsonl.test.ts` + `memory.test.ts` via shared conformance harness (`src/harness/session/testing/conformance.ts`, case at :101 appends an `operation_started` on lane "thread"); reducer-side corruption classification pinned at `packages/agent/test/harness/reducer.test.ts:312-315` ("multiple_open_operations" when a slice carries two).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-upstream", query: "appendRecord already has an open operation lane storage", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt write-time admission control (one open operation per lane, thrown as a storage error from every backend) plus an in-process destination-claim set if session files are timestamped rather than id-addressed. Adapt the error code taxonomy to your host. Omit the claim set if your filenames are content-addressed by unique ids. Coverage: enforced symmetrically in both storages; direct rejection-path test coverage lives in the conformance suite at this pin.
