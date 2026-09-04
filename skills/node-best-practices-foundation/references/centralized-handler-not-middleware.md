<!-- capsule-v2 -->
# Centralized-handler-not-middleware — where does crash-decision logic live so cron jobs and queues get the same treatment as HTTP?

**Source:** nodebestpractices CC-BY-SA-4.0 `master@dc3d60c29d5483d9ea99cf261bbd6203516a2ba7`; Codebase Memory `nodebestpractices`. **Question:** Why must error handling NOT be implemented inside the framework's error middleware, and what is the correct division of labor?

## Middleware forwards, central object decides
**Path/Symbol:** `sections/errorhandling/centralizedhandling.md` (explainer :3-5) + flow example :13.
**Signature:** `ErrorHandler.handleError(error): Promise<void>` — internally `logger.logError → sendMailToAdminIfCritical → saveInOpsQueueIfCritical → determineIfOperationalError`; plus `isTrustedError(error)` from the split capsule.
**Data Shape:** ONE handler object consumed by EVERY entry-point class: HTTP routers, message-queue subscribers, scheduled jobs/cron, `uncaughtException`. The middleware keeps ONLY catch-and-forward responsibility.

### Decisive source
```text
// centralizedhandling.md :5 — the canonical flow
Some module throws an error -> API router catches the error ->
it propagates the error to the middleware ... who is responsible
for catching errors -> a centralized error handler is called.
```
Key negative constraint (same paragraph): placing handling logic IN the middleware means you "won't be able to reuse the same handler for errors that are caught in different scenarios like scheduled jobs, message queue subscribers, and uncaught exceptions."

**Flow:** entry-point catches → forwards verbatim to the singleton handler → handler makes it visible (structured log, metrics via Prometheus/CloudWatch/DataDog/Sentry) → decides crash vs continue per trust flag → HTTP layer additionally maps to response codes at its own edge.
**Invariant:** the decision logic (log format, alerting thresholds, crash predicate) exists in exactly ONE place; every transport funnels into it. Duplicating it per middleware guarantees inconsistent handling between request-time and job-time errors.
**Probe:** no runner upstream. Deterministic probe: `grep -c 'middleware' sections/errorhandling/centralizedhandling.md` ≥ 4 with the explicit reuse warning present.

## Get live surrounding code
**Retrieve:**
**Retrieve:** doc-shaped/BM25-gap note — `search_graph` text queries return ZERO on this graph (Section nodes carry no searchable tokens); use `search_code`, executed live:
```bash
codebase-memory-mcp cli search_code '{"project": "nodebestpractices", "pattern": "centralized", "limit": 10}'
# resolves `sections/errorhandling/centralizedhandling.md` line-exact (verified 2026-08-24)
```

## Verdict
Adopt the forward-only-middleware + singleton-handler split in every multi-entry-point service. Adapt handler internals (which metrics sink, mailer, ops queue). Omit specific vendor choices — swappable infrastructure.
