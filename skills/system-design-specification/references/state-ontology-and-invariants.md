# State Ontology and Invariants — Formal Separation of Data vs Orchestration

Use this reference when designing domain models, multi-agent systems, or storage layers.

## The Core Discipline: Active vs Passive State
Do not lump all state into a single monolithic document or JSON blob. Formally split state into **passive shared data** and **active execution lines**:

```text
1. Shared Passive Data (The DAG / Tree)
   - Append-only nodes linked by parent IDs
   - Immutable once written
   - Contains ZERO execution state, ZERO pointers, ZERO thread IDs
   - Deleting all execution logs leaves a 100% valid conversation history

2. Active Execution Positions (Lanes / Threads)
   - Named pointer to a leaf node in the DAG
   - Owns serialized work, message queues, and mutation line
   - Multiple lanes can diverge from the same DAG node in parallel without coordination

3. Write-Ahead Logs (Operation Logs)
   - Flat, chronological records of intent, attempts, and costs
   - Invisible to user context and LLM prompts
   - Read ONLY by startup recovery to reconstruct uncommitted state

4. Global Facts
   - Session-level metadata with latest-write-wins semantics
```

## How to Formulate Mathematical Invariants
Every system specification must list 5–10 unbreakable invariant rules written as hard constraints:

### Example Invariant List:
- *Invariant 1 (Tree Purity)*: The tree is conversation only. No lane state, no orchestration pointers live in it.
- *Invariant 2 (Parent Immutability)*: An entry's parent chain never changes. Branches share prefixes; nothing is copied.
- *Invariant 3 (Atomic Advances)*: A lane's leaf moves in exactly two ways: appending an entry chained to its current leaf, or explicit navigation.
- *Invariant 4 (Isolation)*: Operation-log records never affect the tree. Deleting every operation log leaves a complete, valid conversation.
- *Invariant 5 (Single Execution Line)*: At most one operation is open per lane. More than one open operation is treated as storage corruption.

## Designing Invariants into Code
Turn each invariant into a concrete check in the codebase:
```ts
function assertSessionInvariant(session: Session) {
  for (const [laneName, lane] of session.lanes) {
    const openOps = findOpenOperations(lane);
    if (openOps.length > 1) {
      throw new InvariantViolation(`Lane ${laneName} has ${openOps.length} open operations`);
    }
  }
}
```
