<!-- capsule-v2 -->
# Graceful-shutdown choreography — what must happen in order when a container gets SIGTERM?

**Source:** nodebestpractices CC-BY-SA-4.0 `master@dc3d60c29d5483d9ea99cf261bbd6203516a2ba7`; Codebase Memory `nodebestpractices`. **Question:** What ordered steps make a shutdown drain in-flight requests instead of dropping thousands of users?

## Drain → stop-new → cleanup → log, all inside the SIGTERM budget
**Path/Symbol:** `sections/docker/graceful-shutdown.md` (explainer :3-5, phases :33) + `sections/docker/bootstrap-using-node.md` (signal plumbing).
**Signature:** SIGTERM handler orchestration, no single API. Required parts: tell the load balancer the app is not ready (health-check flip), wait for in-flight requests to finish, stop accepting new requests, clean up resources, log useful info before dying.
**Data Shape:** Kubernetes gives a 30-second SIGTERM grace period (:3). Keep-alive connections must be told to re-establish; the `stoppable` library (hunterloftis/stoppable) helps close keep-alives cleanly (:3).

### Decisive source
```text
// graceful-shutdown.md :3 — the ordered contract
the shutdown code should wait until all ongoing requests are flushed out
and then clean-up resources ... it demands orchestrating several parts:
Tell the LoadBalancer that the app is not ready to serve more requests
(via health-check), wait for existing requests to be done, avoid handling
new requests, clean-up resources and finally log some useful information
before dying.
```

**Flow:** SIGTERM → deregister from LB (health-check returns unhealthy) → stop accepting new connections → drain in-flight → close keep-alives (stoppable) → release resources → log → exit. This must complete within the runtime's grace budget (30 s in K8s).
**Invariant:** dying immediately is the failure — "not responding to thousands of disappointed users" (README 8.6). The drain must be bounded by the grace period so the orchestrator doesn't SIGKILL mid-cleanup. Requires Node to be PID1 (see `node-direct-bootstrap`) so it actually receives the signal.
**Probe:** no runner upstream. Deterministic probes (re-derived & executed 2026-08-24, erratum below): `grep -c 'SIGTERM' sections/docker/graceful-shutdown.md` = 1; `grep -c 'stoppable' sections/docker/graceful-shutdown.md` = 1; `grep -c 'LoadBalancer' sections/docker/graceful-shutdown.md` = 1. ERRATUM: this capsule originally shipped `grep -c 'SIGTERM\|stoppable\|LoadBalancer' …` ≥ 3 — silently dead through two verification sweeps (alternation counts LINES containing ANY term; the doc mentions each term exactly once, on different lines, so the true value is 1, never 3). Count terms individually.

## Get live surrounding code
**Retrieve:**
**Retrieve:** doc-shaped/BM25-gap note — `search_graph` text queries return ZERO on this graph (Section nodes carry no searchable tokens); use `search_code`, executed live:
```bash
codebase-memory-mcp cli search_code '{"project": "nodebestpractices", "pattern": "graceful", "limit": 10}'
# resolves `sections/docker/bootstrap-using-node.md`, `sections/docker/graceful-shutdown.md` line-exact (verified 2026-08-24)
```

## Verdict
Adopt the ordered drain choreography for any containerized service. Adapt the LB-deregistration mechanism and grace budget per orchestrator. Omit the specific stoppable library if your runtime handles keep-alives.
