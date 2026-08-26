<!-- capsule-v2 -->
# Throttler queue sorting ladder — how does a shared priority queue avoid starvation AND deterministic thundering herds at the same time?

**Source:** growchief AGPL-3.0 `main@abb1e37a`; Codebase Memory `growchief`. **Question:** what is the total order on queued jobs when many workflows (same priority) compete for one account's action budget?

## Random per-workflow weight inside a deterministic comparator
**Path/Symbol:** `apps/orchestrator/src/workflows/workflow.throttle.ts:sortFunction` (:76-99).
**Signature:** `(items: Work[]) => ((a: Work, b: Work) => number)` — a factory: it first assigns weights, then returns the comparator.
**Data Shape:** `weight = new Map()` keyed by workflowId, each id gets ONE `Math.random()` per sort invocation; comparisons fall through 4 levels.

### Decisive source
```ts
const weight = new Map();
for (const it of items) {
  if (!weight.has(it.workflowId)) {
    weight.set(it.workflowId, Math.random()); // one random number per workflowId
  }
}
return (a: Work, b: Work) => {
  if (a.priority !== b.priority) return a.priority - b.priority; // 1) priority asc
  const wa = weight.get(a.workflowId), wb = weight.get(b.workflowId);
  if (wa !== wb) return wa - wb;                                 // 2) random by workflowId
  if (a.date !== b.date) return a.date - b.date;                 // 3) date asc
  return String(a.workflowId).localeCompare(String(b.workflowId)); // 4) tiebreak
};
```

**Flow:** every enqueue and every re-queue re-sorts the whole array with a FRESH random draw per workflowId — so within one priority tier, all jobs of workflow A run before all jobs of workflow B for that pass, but WHICH workflow goes first changes each sort.
**Invariant:** the weight map is built from the CURRENT array contents on every call, making the comparator self-consistent for that single sort (comparator consistency within one sort call is what JS Array.prototype.sort requires); the final localeCompare guarantees a total order so sort is deterministic given the weights. Priority −1 is reserved for leadList imports (`workflow.upload.leads.ts` enqueues with `priority: -1`), which therefore always outrank user tools.
**Probe:** no test runner upstream. Deterministic pins: `grep -n 'priority asc' apps/orchestrator/src/workflows/workflow.throttle.ts` → :87; `grep -n "priority: -1" apps/orchestrator/src/workflows/workflow.upload.leads.ts` → :46.
**Why a porter gets it wrong:** sorting by date alone starves big workflows under small ones forever; sorting by workflowId alone makes the same workflow always win after restarts. The per-sort random tier breaks both failure modes while keeping priority absolute.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "growchief", query: "sortFunction", limit: 3, fields: ["lines"] });
```

## Verdict
Adopt the 4-level comparator shape (priority → randomized group → FIFO date → id tiebreak). Adapt the randomization source (crypto-random or round-robin rotation also work — the requirement is only freshness per sort + stability within one sort). Omit nothing else; this is pure logic.
