<!-- capsule-v2 -->
# Cross-process budget ledger — how do you cap spend across a tree of child processes that each live in their own OS process?

**Source:** pi-fabric MIT `feat/veda-runner@4874ac3a`; Codebase Memory `pi-fabric`. **Question:** what makes an append-only JSONL file a safe shared budget, and where does the ceiling deliberately leak?

## Env-propagated ledger with check-before-spawn and append-after-settle
**Path/Symbol:** `src/agents/budget-ledger.ts` whole (:1-210); consumption `src/agents/manager.ts:410-417` (init/inherit), `:509-516` (check-before-spawn), `:1240-1256` (#appendAttributedBudgetLedger + summary-cache invalidation).
**Signature:** `activeBudgetState(): State|undefined`; `initBudgetLedger(budget): State`; `readBudgetLedger(file): {cost, tokens}`; `appendBudgetLedger(file, entry)`; `readBudgetLedgerDetailed(file): Detail` (byRunner/byActor rollups).
**Data Shape:** env triple `PI_FABRIC_BUDGET / PI_FABRIC_BUDGET_FILE / PI_FABRIC_BUDGET_ID`; entries `{id, depth, cost, tokens, ts, runner?, actorId?, actorName?, input?...}`; only depth-0 with `budgetUsd>0` initializes; descendants inherit via `{...process.env}` forwarding.

### Decisive source
```ts
// header comment, load-bearing:
// The check is best-effort (concurrent children can each pass the check before
// any cost lands, so a tree may slightly overshoot), while the race-free
// ceiling remains the per-execution call count (agents.maxPerExecution).
// Cost is recorded only after a child finishes ...
// O_APPEND makes small single-line writes atomic across concurrent writers on POSIX

if (this.#budget) {
  const spent = readBudgetLedger(this.#budget.file).cost;
  if (spent >= this.#budget.budget)
    throw new Error(`Fabric recursion budget exceeded: spent $${spent.toFixed(6)} ...`);
}
```

**Flow:** root creates tmpdir ledger + seeds env → every spawn re-reads the WHOLE file and refuses when spent ≥ budget → after each child settles the manager appends ONE attributed line (streamed `tokens.usage` lifecycle events accumulate into `usageEmitted`, and settlement flushes only the residual gap so nothing double-counts) → close removes the owned ledger dir and unsets env so a long-lived host cannot leak a budget into a later session.
**Invariant:** tolerance over strictness — malformed lines are skipped on read (a single bad entry never aborts accounting) and write failures are swallowed (budget must not break runs); the documented overshoot race is accepted because a hard per-execution call cap exists one layer up. A porter who "fixes" the race with a lock adds cross-process contention for a guarantee the design explicitly delegates elsewhere.
**Probe:** `tests/budget-ledger.test.ts:51` ("sums appended entries and tolerates malformed lines"), :74 (runner/actor attribution rollups), :114 (backward-compatible flat rows); settlement-gap behavior pinned indirectly via agent-manager usage tests (:147 relay of normalized token events).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-fabric", query: "appendBudgetLedger readBudgetLedger PI_FABRIC_BUDGET", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the env-inherited append-only ledger + residual-flush accounting for any multi-process spend/token cap; adapt attribution fields to your orchestrator; omit the detailed rollups unless you show per-actor costs. Direct unit tests cover parsing/attribution; the overshoot caveat is documented IN-SOURCE — record it in-capsule.
