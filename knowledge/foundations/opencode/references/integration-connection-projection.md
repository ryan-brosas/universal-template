<!-- capsule-v2 -->
# Integration connection projection — how do you present "which credentials can this integration use right now" from a registry that deliberately stores no connection state?

**Source:** opencode MIT `dev@03521003fafd`; Codebase Memory `opencode`. **Question:** The integration registry (State draft) records only integrations, methods, and OAuth implementations. Connections — stored credentials AND detected environment variables — change independently of registration. Where do connections come from at read time, and what ordering/refresh rules apply?

## Connections are projected per read from the credential store plus live env
**Path/Symbol:** `packages/core/src/integration.ts` (`resolveConnections` :288-301, `project` :303-307, `connection.active` :369-372, `connection.resolve` :373-392, `connection.key` :393-405, `connection.update`/`remove` :406-425).
**Signature:** `resolveConnections(entry: Entry | undefined, saved: readonly Credential.Info[]) → IntegrationConnection.Info[]`; `connection.active(id) → Effect<IntegrationConnection.Info | undefined>`; `connection.resolve(connection) → Effect<Credential.Value | undefined, AuthorizationError>`.
**Data Shape:** connection = `{type:"credential", id, label} | {type:"env", name}`; Info = {id, name, methods, connections}.

### Decisive source
```ts
// integration.ts:288-301 — stored credentials newest-first, then env vars that exist NOW
const resolveConnections = (entry: Entry | undefined, saved: readonly Credential.Info[]) => {
  const credentials = saved
    .map((credential) => ({ type: "credential" as const, id: credential.id, label: credential.label }))
    .toReversed()
  const env = (entry?.methods ?? [])
    .filter((method) => method.type === "env")
    .flatMap((method) => method.names.filter((name) => process.env[name]))
    .map((name) => ({ type: "env" as const, name }))
  return [...credentials, ...env]
}
```

**Flow:** `get`/`list` join the registry entry with `credentials.list(id)` (list groups ALL credentials by integrationID first) and project through resolveConnections; `connection.active` is simply `resolveConnections(...)[0]` — the newest stored credential wins, falling back to the first detected env var. `connection.resolve` turns a connection into usable material: env → `process.env[name]` read at call time; credential → its value, and if the value is OAuth with a `refresh` implementation and expires within 5 minutes, run `implementation.refresh` and `credentials.update` (failures map to `AuthorizationError{cause}` via the `authorize` wrapper). `connection.key` requires a registered key method (missing method is `Effect.die` — a defect, not a typed error), then `credentials.create` + publishes `ConnectionUpdated` and `Updated`. `update`/`remove` re-publish both events only when the credential existed.
**Invariant:** the registry draft NEVER stores connections — creating or deleting a credential changes projection output without any transform/reload (test pins the exact connections array after two creates); env detection is live per read (test deletes the env var in the release phase and the projection follows); newest-credential-first ordering makes `active` deterministic without timestamps in the projection type; OAuth refresh is lazy and threshold-gated (5 minutes), not scheduled.
**Probe:** `packages/core/test/integration.test.ts` (349L, 9 `it.effect`): "connects with a key and stores the credential" pins key storage + one Updated event; "projects credential and env connections" pins the exact [credential-newest, env] array and active() = first element; "completes code OAuth once and stores the credential" pins the settle→credentials.create path that feeds this projection (see integration-oauth-attempt-machine for the attempt side). Source pin:
```bash
grep -c 'resolveConnections' packages/core/src/integration.ts  # expect 4
grep -c 'toReversed' packages/core/src/integration.ts          # expect 1
grep -c 'it.effect' packages/core/test/integration.test.ts     # expect 9
```

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "opencode", query: "Integration resolveConnections project connections credential env active resolve refresh threshold", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt stateless connection projection: keep the registry pure, derive connections per read from the credential store (newest-first) plus live environment detection, and make `active` = first projection element. Adopt the lazy 5-minute-threshold OAuth refresh with refresh-failure mapped to a typed error. Adapt the projection types to your credential schema; omit the Effect error-channel mapping if your host uses exceptions. Coverage caveat: the refresh path inside connection.resolve is source-confirmed only (no direct test pins it at this pin — carried from the pass-14 caveat); Codebase Memory MCP not connected this session — Retrieve marked for re-execution on graph reconnect; bun runner blocked at this checkout, probes are byte-exact greps.
