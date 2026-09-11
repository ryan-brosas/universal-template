<!-- capsule-v2 -->
# Unhandled-rejection funnel — why do promise errors vanish even with an uncaughtException handler installed?

**Source:** nodebestpractices CC-BY-SA-4.0 `master@dc3d60c29d5483d9ea99cf261bbd6203516a2ba7`; Codebase Memory `nodebestpractices`. **Question:** How do you guarantee no async error disappears silently, and what is the correct wiring between `unhandledRejection` and `uncaughtException`?

## Rejection→exception rethrow funnel
**Path/Symbol:** `sections/errorhandling/catchunhandledpromiserejection.md` (explainer :7, JS funnel :28-36, TS funnel :48-56).
**Signature:** `process.on('unhandledRejection', (reason, p) => { throw reason; })` paired with `process.on('uncaughtException', error => { handleError(error); if (!isTrustedError(error)) process.exit(1); })`.
**Data Shape:** input: any rejected promise lacking a local `.catch`/try-catch. The funnel converts it into a synchronous-style exception so ONE downstream path handles everything. Key negative fact (:11-14): errors thrown inside a `.then` callback are invisible to BOTH local try-catch around the chain construction and to `uncaughtException`.

### Decisive source
```javascript
// catchunhandledpromiserejection.md :28-36
process.on('unhandledRejection', (reason, p) => {
  // caught an unhandled promise rejection — rethrow into the
  // existing fallback handler for unhandled errors
  throw reason;
});
process.on('uncaughtException', (error) => {
  errorManagement.handler.handleError(error);
  if (!errorManagement.handler.isTrustedError(error))
    process.exit(1);
});
```

**Flow:** promise rejects without a local catch → runtime emits `unhandledRejection` (NOT `uncaughtException`) → funnel rethrows reason → lands in `uncaughtException` → shared `handleError` → trust-check decides exit. Discipline layer on top: still add `.catch` per chain and redirect to the same central handler; the process-level hook is the graceful fallback because developer discipline is "somewhat fragile" (:7).
**Invariant:** exactly ONE terminal handling path — the funnel must rethrow into the shared handler, never log-and-swallow at the rejection site (that forks the error strategy into two inconsistent behaviors).
**Probe:** no runner upstream. Deterministic probe: `grep -c "throw reason" sections/errorhandling/catchunhandledpromiserejection.md` = 2 (JS+TS twins); James Nelson quiz block present proving three swallow-shapes exist.

## Get live surrounding code
**Retrieve:**
**Retrieve:** doc-shaped/BM25-gap note — `search_graph` text queries return ZERO on this graph (Section nodes carry no searchable tokens); use `search_code`, executed live:
```bash
codebase-memory-mcp cli search_code '{"project": "nodebestpractices", "pattern": "unhandledRejection", "limit": 10}'
# resolves `sections/errorhandling/catchunhandledpromiserejection.md` line-exact (verified 2026-08-24)
```

## Verdict
Adopt the funnel pattern verbatim for any promise-based runtime (Node; analogous patterns exist for other runtimes' rejection hooks). Adapt event names to the platform. Omit old Node warning-message behavior discussion — version-specific noise.
