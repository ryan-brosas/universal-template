<!-- capsule-v2 -->
# Event-loop non-blocking — what single-threaded trap makes one request stall 3000 others?

**Source:** nodebestpractices CC-BY-SA-4.0 `master@dc3d60c29d5483d9ea99cf261bbd6203516a2ba7`; Codebase Memory `nodebestpractices`. **Question:** Which operations block the event loop, and how do you offload them so concurrent requests stay responsive?

## Keep per-client work small; offload CPU-bound work
**Path/Symbol:** `sections/performance/block-loop.md` (explainer :1, blocking example :7-13, benchmark :26-34) + README 7.1.
**Signature:** discipline, not API. Blocking ops: high-complexity math, large JSON parsing, big-array logic, unsafe regex, large I/O. Remedies: offload to a dedicated service/job server, or break long tasks into small steps on the Worker Pool.
**Data Shape:** the doc's concrete evidence — a 30 ms `while`-loop `sleep` inside a route turns a ~300 ms median latency into 3000+ concurrent users waiting; the clinic benchmark shows 300.56 ms avg latency and ~32 req/s.

### Decisive source
```javascript
// block-loop.md :7-13 — the anti-pattern
function sleep (ms) {
  const future = Date.now() + ms
  while (Date.now() < future);   // busy-wait blocks the event loop
}
server.get('/', (req, res, next) => {
  sleep(30)                      // every request now stalls the loop
  res.send({})
  next()
})
```
Rule of thumb (Node docs quote, same file): "Node.js is fast when the work associated with each client at any given time is 'small'."

**Flow:** event loop rotates through queues on one thread → a CPU-bound task occupies it → all other requests queue behind it → latency spikes. Fix by shrinking per-request work or moving heavy compute off-thread.
**Invariant:** the event loop must never be held by a long synchronous task; keep per-client work small and offload CPU-intensive work (dedicated process, worker pool, or external job service).
**Probe:** no runner upstream. Deterministic probe: `grep -c 'clinic doctor' sections/performance/block-loop.md` = 1 with the 300.56 ms benchmark row present.

## Get live surrounding code
**Retrieve:**
**Retrieve:** doc-shaped/BM25-gap note — `search_graph` text queries return ZERO on this graph (Section nodes carry no searchable tokens); use `search_code`, executed live:
```bash
codebase-memory-mcp cli search_code '{"project": "nodebestpractices", "pattern": "clinic doctor", "limit": 10}'
# resolves `sections/performance/block-loop.md` line-exact (verified 2026-08-24)
```

## Verdict
Adopt the keep-it-small + offload discipline for any single-threaded async runtime. Adapt the offload mechanism (worker_threads, cluster, job server) per scale. Omit the clinic/autocannon tooling specifics — measurement tooling, not contract.
