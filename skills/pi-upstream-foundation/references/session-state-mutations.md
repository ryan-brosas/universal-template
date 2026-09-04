<!-- capsule-v2 -->
# Single-writer mutation state — how do entries, records, and lane pointers stay consistent under one append path?

**Source:** pi-upstream MIT `main@a470b121bf683b4c2b9fc0b3a7c807de7e0cfe9c`; Codebase Memory `pi-upstream`. **Question:** A porter lets callers write entries directly and keeps derived state (leaf pointers, stats) as side effects — what breaks, and how does pi structure the single choke point instead?

## SessionState.applyMutation: every change is one validated, consecutively-numbered mutation
**Path/Symbol:** `packages/agent/src/harness/session/state.ts:97-180` (`applyMutation`), `:50-67` (indexes), `:260-299` (`createForkMutations`), `:301-320` (`walkToRoot`).
**Signature:** `applyMutation(mutation: SessionMutation, invalid?): void` where `SessionMutation = {kind:"entry"; lane?; entry} | {kind:"record"; record} | {kind:"lane"; seq; lane; leafId} | {kind:"fact"; seq; fact:"name"|"label"; ...}`.
**Data Shape:** State holds `entries[] + entriesById`, `records[] + openOperationsByLane (Map<lane, Map<recordId, OperationStartedRecord>>)`, `lanes Map (seeded [["main", null]])`, monotonically growing `log[]`, accumulated `stats`. Entry types: message / model_change / thinking_level_change / active_tools_change / compaction / branch_summary / custom. Record types: operation_started / abort_requested / operation_finished / step_attempt / tool_started / queue_enqueued / queue_cancelled / write_deferred / usage.

### Decisive source
```ts
const seq = /* mutation's seq */;
if (seq !== this.sequence + 1) invalid(`has non-consecutive seq ${seq}`);
switch (mutation.kind) {
    case "entry": {
        if (this.usedIds.has(mutation.entry.id)) invalid(`contains duplicate id ${mutation.entry.id}`);
        if (mutation.lane !== undefined) {
            const leafId = this.lanes.get(mutation.lane);
            if (leafId === undefined) invalid(`references missing lane ${mutation.lane}`);
            if (mutation.entry.parentId !== leafId) invalid("does not chain to the lane leaf");
        }
```

**Flow:** every writer (memory storage inline; JSONL storage inside its enqueue queue after a successful file append) funnels through `applyMutation`; it rejects non-consecutive seq, duplicate ids, entries whose `parentId` ≠ the appending lane's current leaf (lane-bound writes), missing parents/lane targets, then advances `sequence`, updates indexes/pointers/log/stats in one step. Branch reads walk child→root with cycle detection (`walkToRoot` throws on revisited id). Fork materializes as a fresh mutation stream (`createForkMutations`): cloned entries renumbered from 1 → lane pointers → name fact → label facts.
**Invariant:** Exactly ONE write path exists; all structural relationships (seq consecutiveness, id uniqueness, lane-leaf chaining) are validated there, so no backend can persist a structurally impossible history. Stats accumulate ONLY from `usage` records with the asymmetric rule `cachedTokens += usage.cacheRead; uncachedTokens += usage.input + usage.cacheWrite` (:143-148) — cacheWrite counts as UNCACHED. Fork mutations carry entries+lanes+facts but deliberately DROP records (usage totals restart at zero in the child; jsonl.test.ts "recomputes fork message counts when reopening" :325).
**Probe:** `packages/agent/test/harness/session/jsonl.test.ts:514-566` ("rejects an imported entry that references a missing parent", "rejects a lane-bound entry that does not chain to the lane leaf", "does not move a lane for an imported entry without lane metadata"); conformance harness `src/harness/session/testing/conformance.ts` cases :101/:149/:233.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-upstream", query: "SessionState applyMutation sequence lane leaf", limit: 10, fields: ["signature", "name", "file"] });
```
(Resolves `state.ts:97-180` rank #1.)

## Verdict
Adopt the single validated mutation choke point with consecutive-seq enforcement and lane-chaining checks; derive stats only from usage records with the cacheRead/cacheWrite asymmetry made explicit; implement fork as renumbered entry-mutation replay that intentionally drops records. Adapt the entry/record vocabulary to your domain. Omit multi-lane support only if your host truly runs one linear conversation. Coverage: direct JSONL import-validation tests at this pin; memory-backend path exercised via conformance suite.
