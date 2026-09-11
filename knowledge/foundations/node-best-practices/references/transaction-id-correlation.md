<!-- capsule-v2 -->
# Transaction-id correlation — how do you keep one request's log lines linkable across async calls and microservices?

**Source:** nodebestpractices CC-BY-SA-4.0 `master@dc3d60c29d5483d9ea99cf261bbd6203516a2ba7`; Codebase Memory `nodebestpractices`. **Question:** How do you attach a single correlation id to every log line of one request, including across service boundaries — and what are the documented restrictions and fallbacks for the storage mechanism?

## AsyncLocalStorage carries the id; x-transaction-id header crosses services; CLS is the pre-ALS fallback
**Path/Symbol:** `sections/production/assigntransactionid.md` (explainer :3, ALS example :11-14, cls-rtracer helper :95-140, NOTICE restrictions :145-147, continuation-local-storage fallback :155-175) + `sections/production/smartlogging.md` (:3) + `sections/production/logrouting.md` (:3).
**Signature:** Node built-in `AsyncLocalStorage` (from `node:async_hooks`) to keep the same context across async calls; propagate cross-service via an HTTP header like `x-transaction-id`; on runtimes without ALS, `continuation-local-storage`'s `createNamespace('...')` per-request store.
**Data Shape:** input: one request spanning many async hops (and possibly many machines). Output: every log line in that flow carries the same `transaction-id` so a single suspicious line can be traced to its whole request context. Documented restrictions on ALS (:145-147): requires Node v14+; built on `async_hooks`, which is still experimental — performance fears are "very negligible, but you should make your own considerations".

### Decisive source
```text
// assigntransactionid.md :3 — why
A typical log is a warehouse of entries from all components and requests.
Upon detection of some suspicious line or error, it becomes hairy to match
other lines that belong to the same specific flow ... assign a unique
transaction identifier value to all the entries from the same request ...
When calling other microservices, pass the transaction id using an HTTP
header like "x-transaction-id" to keep the same context.
// :145-147 — the two documented restrictions
NOTICE: there are two restrictions on using async-local-storage:
1. It requires Node v.14.
2. It is based on a lower level construct in Node called async_hooks which
is still experimental, so you may have the fear of performance problems.
Even if they do exist, they are very negligible, but you should make your
own considerations.
// :157-158 — the fallback shape
const { createNamespace } = require('continuation-local-storage');
const session = createNamespace('my session');
```

**Flow:** on request entry, extract the id from the incoming `x-transaction-id` header or generate `uuid()` if absent → store it in AsyncLocalStorage → every log call in that async flow reads the id from the store → at service boundaries, forward it in `x-transaction-id` so downstream services log the same id. Combined with smart logging (JSON + contextual props, smartlogging.md) and stdout routing (logrouting.md), the ops team can reconstruct a full transaction. Pre-ALS runtimes: same choreography with a `continuation-local-storage` namespace instead of ALS (:155-175); helper libraries (cls-rtracer) wrap both the storage and the header echo/use config.
**Invariant:** the id must be derived ONCE per request (respect an upstream header, never re-derive at each hop) and survive async hops (ALS/CLS, not a closure-scoped variable that a `.then` boundary drops) and service hops (explicit header). Without it, "looking at a production error log without the context… makes it much harder and slower to reason about the issue" (README 5.14).
**Probe:** no runner upstream. Deterministic probe: `grep -c 'x-transaction-id\|AsyncLocalStorage' sections/production/assigntransactionid.md` ≥ 2 && `grep -c 'continuation-local-storage' sections/production/assigntransactionid.md` = 2 && `grep -c 'requires Node v.14' sections/production/assigntransactionid.md` = 1.
**Retrieve:** doc-shaped/BM25-gap note — `search_graph` text queries return ZERO on this graph (Section nodes carry no searchable tokens); use `search_code`, executed live:
```bash
codebase-memory-mcp cli search_code '{"project": "nodebestpractices", "pattern": "continuation-local-storage", "limit": 10}'
# resolves `sections/production/assigntransactionid.md` Module 1-198 lines 155;157 (English hit among 9 translation twins; verified 2026-08-26)
codebase-memory-mcp cli search_code '{"project": "nodebestpractices", "pattern": "AsyncLocalStorage", "limit": 10}'
# resolves `sections/production/assigntransactionid.md` line-exact (verified 2026-08-24)
```

## Verdict
Adopt ALS-based correlation + header propagation for any async service on modern Node. Adapt the header name and storage mechanism per runtime: ALS is Node-specific (other runtimes use context-vars/thread-local), and pre-v14 Node falls back to continuation-local-storage with the same once-per-request + explicit-header contract. Omit nothing behavioral — cross-async-hop survival is the contract; carry the async_hooks-experimental caveat into any performance review of the design.
