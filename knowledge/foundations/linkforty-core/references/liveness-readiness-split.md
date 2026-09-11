<!-- capsule-v2 -->
# Liveness vs readiness split — /health never touches the DB; Redis failure degrades but never flips readiness

**Source:** LinkForty core AGPL-3.0-only `main@8919b1ecdc48f8c53340c4590b5f0eae0680abf8`; Codebase Memory `ext-core`. **Question:** Which dependencies may fail a container-health probe, and which must only report degraded?

## healthRoutes two-level probes
**Path/Symbol:** `src/routes/health.ts:healthRoutes` (:25-58); registration order matters (`src/index.ts:62` — health registered BEFORE redirectRoutes).
**Signature:** `GET /health` → `{ status: 'ok', uptime }` (no deps); `GET /health/ready` → 200 `{ status:'ok', checks:{database:'ok', redis?} }` or 503 `{ status:'error', checks }`.
**Data Shape:** `checks.database` from `SELECT 1`; `checks.redis` from `PING` only when fastify.redis is configured.

### Decisive source
```ts
// health.ts:42-53 — the asymmetric severity rule:
if (fastify.redis) {
  try { await fastify.redis.ping(); checks.redis = 'ok'; }
  catch {
    // Redis is an optional cache with database fallback, so a failure here
    // is degraded, not unready — it must not flip the overall status.
    checks.redis = 'error';
  }
}
const ready = checks.database === 'ok';
return reply.status(ready ? 200 : 503).send({ ... });
```

**Flow:** liveness answers purely from process state so a database blip cannot get the container killed by an orchestrator that restarts on failing probes → readiness confirms the database and reports Redis as informational → 503 lets a load balancer drain the instance. Static paths are chosen by Fastify's router over parametric `/:shortCode`, which ALSO means `/health` was previously swallowed by the catch-all short-code route — answered as a lookup (404, or 500 self-hosted) making the Docker HEALTHCHECK permanently unhealthy (issue #35, :5-10 comment).
**Invariant:** Liveness = zero dependency touches; readiness gate = ONLY the store of record; optional caches report but never decide; static health paths must be registered before parametric routes (and consequently those names are unavailable as short codes).
**Probe:** `bash -c "grep -cF 'degraded, not unready' src/routes/health.ts"` → 1 (:47); direct tests `src/routes/health.test.ts`: it('never touches the database...'), it('is 503 when the database is unreachable'), it('reports a failing Redis as degraded, not unready') + describe('regression: /health is not swallowed by the redirect route').

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-core", query: "health ready liveness redis degraded", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the liveness/readiness split with per-dependency severity classification; adapt check set; omit nothing — the asymmetry rule (optional dep ⇒ degraded-not-unready) is the whole port.
