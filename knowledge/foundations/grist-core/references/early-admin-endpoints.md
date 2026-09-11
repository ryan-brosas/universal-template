<!-- capsule-v2 -->
# Early admin/install endpoints — how do you keep a rescue panel reachable when the rest of the server is broken?

**Source:** grist-core MIT `main@b83224bbe9c88910dfeb28922df254a26f702f68`; Codebase Memory `grist-core`. **Question:** Admin tooling must work during partial failure — what middleware is deliberately (not) attached, and how are install prefs/configs served and audited?

## Minimal-middleware baseline + admin gate on /api/admin & /api/install only; env-over-db prefs with source labels
**Path/Symbol:** `app/server/lib/attachEarlyEndpoints.ts`: `attachEarlyEndpoints` (71–397), admin route with minimal middleware rationale comment (74–88), `requireInstallAdmin` gate (90–96), prefs GET/PATCH (140–213), permissions status view (149–167), config CRUD (233–326), audit loggers (328–396), `pruneConfigAPIResult` allowlist (399–416).
**Signature:** `attachEarlyOptions({ app, gristServer, userIdMiddleware })` — ONLY userIdMiddleware is guaranteed present.
**Data Shape:** `PermissionsStatus` entries `{ value, source: "environment-variable" | "preferences" | undefined }`; config rows pruned to `{id,key,value,createdAt,updatedAt,org{id,name,domain}}`.

### Decisive source
```ts
// Admin endpoint needs to have very little middleware since each
// piece of middleware creates a new way to fail and leave the admin
// panel inaccessible. Generally the admin panel should report problems
// rather than failing entirely.
app.get("/admin/:subpath(*)?", userIdMiddleware, expressWrap(async (req, res) => {
  return gristServer.sendAppPage(req, res, { path: "app.html", status: 200,
    config: makeAdminPageConfig(gristServer) });
}));
const adminMiddleware = [requireInstallAdmin];
app.use("/api/admin", adminMiddleware);
app.use("/api/install", adminMiddleware);
```

**Flow:** these routes register FIRST in server boot so nothing upstream can break them; the page renders via sendAppPage reporting degraded state instead of erroring. Prefs PATCH writes DB prefs then pushes env vars through `appSettings.setEnvVars` + `invalidateReloadableSettings(...keys)` so live settings re-read; edition values are guarded by `GristEdition.guard` before persisting. Config CRUD validates the KEY against a checker registry, then the VALUE via `ConfigValueCheckers[key].check(body)` → 400 with `userError` details; responses pass through a positive pick-list prune; every create/update/delete emits an audit event carrying previous+current snapshots.
**Invariant:** middleware additions to the early plane are treated as new failure modes — anything beyond userIdMiddleware needs justification; install-admin gating is applied at router mount level so no route can forget it; config reads/writes never leak raw entity fields.
**Probe:** `test/server/lib/BootProbes.ts` pins probe/status surface; config CRUD exercised in `test/gen-server` ApiServer suites; direct unit test of attachEarlyEndpoints absent at this pin — caveat.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "grist-core",
  query: "attachEarlyEndpoints requireInstallAdmin getPrefsWithSources updatePrefs invalidateReloadableSettings", limit: 10,
  fields: ["signature", "name", "file"] });
```

## Verdict
Adopt for any self-hosted product: ship a minimal-dependency admin plane that mounts before the full stack, gate its API with one explicit role check, label every setting's source, and report failures inline. Adapt pref keys/edition guard to your product. Omit telemetry/version-check routes if irrelevant.
