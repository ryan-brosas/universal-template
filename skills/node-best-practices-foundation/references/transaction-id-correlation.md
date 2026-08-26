<!-- capsule-v2 -->
# Transaction-id correlation — how do you keep one request's log lines linkable across async calls and microservices?

**Source:** nodebestpractices CC-BY-SA-4.0 `master@dc3d60c29d5483d9ea99cf261bbd6203516a2ba7`; Codebase Memory `nodebestpractices`. **Question:** How do you attach a single correlation id to every log line of one request, including across service boundaries?

## AsyncLocalStorage carries the id; x-transaction-id header crosses services
**Path/Symbol:** `sections/production/assigntransactionid.md` (explainer :3, ALS example :11-14) + `sections/production/smartlogging.md` (:3) + `sections/production/logrouting.md` (:3).
**Signature:** Node built-in `AsyncLocalStorage` (from `node:async_hooks`) to keep the same context across async calls; propagate cross-service via an HTTP header like `x-transaction-id`.
**Data Shape:** input: one request spanning many async hops (and possibly many machines). Output: every log line in that flow carries the same `transaction-id` so a single suspicious line can be traced to its whole request context.

### Decisive source
```text
// assigntransactionid.md :3 — why
A typical log is a warehouse of entries from all components and requests.
Upon detection of some suspicious line or error, it becomes hairy to match
other lines that belong to the same specific flow ... assign a unique
transaction identifier value to all the entries from the same request ...
When calling other microservices, pass the transaction id using an HTTP
header like "x-transaction-id" to keep the same context.
// :11-14 — the mechanism
sharing TransactionId among request functions and between services using
async-local-storage ... the Node alternative to thread local storage ...
a storage for asynchronous flows in Node.
```

**Flow:** on request entry, store `uuid()` in AsyncLocalStorage → every log call in that async flow reads the id from ALS → at service boundaries, forward it in `x-transaction-id` so downstream services log the same id. Combined with smart logging (JSON + contextual props, smartlogging.md) and stdout routing (logrouting.md), the ops team can reconstruct a full transaction.
**Invariant:** the id must be derived ONCE per request and survive async hops (ALS, not a closure-scoped variable that a `.then` boundary drops) and service hops (explicit header, not re-derived). Without it, "looking at a production error log without the context… makes it much harder and slower to reason about the issue" (README 5.14).
**Probe:** no runner upstream. Deterministic probe: `grep -c 'x-transaction-id\|AsyncLocalStorage' sections/production/assigntransactionid.md` ≥ 2.

## Get live surrounding code
**Retrieve:**
**Retrieve:** doc-shaped/BM25-gap note — `search_graph` text queries return ZERO on this graph (Section nodes carry no searchable tokens); use `search_code`, executed live:
```bash
codebase-memory-mcp cli search_code '{"project": "nodebestpractices", "pattern": "AsyncLocalStorage", "limit": 10}'
# resolves `sections/production/assigntransactionid.md` line-exact (verified 2026-08-24)
```

## Verdict
Adopt ALS-based correlation + header propagation for any async service. Adapt the header name and storage mechanism per runtime (ALS is Node-specific; other runtimes use context-vars/thread-local). Omit nothing — cross-async-hop survival is the contract.
