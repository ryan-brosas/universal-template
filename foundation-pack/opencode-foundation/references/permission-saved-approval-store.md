<!-- capsule-v2 -->
# PermissionSaved store — where do "always allow" approvals live and how do they re-enter evaluation?

**Source:** opencode MIT `dev@03521003fafd`; Codebase Memory `opencode`. **Question:** how are remembered approvals persisted, scoped, and re-read so they behave as rules rather than a side-channel?

## Connected graph-selected seam
**Path/Symbol:** `packages/core/src/permission/saved.ts`: `list` (:33-41), `add` (:43-56), `remove` (:58-61); consumed by `packages/core/src/permission.ts` `savedRules` (:94-98) and `reply` always-branch (:210-224).
**Signature:** `add: (input: {projectID, action, resources[]}) => Effect<void>`; `list: (input?: {projectID?}) => Effect<ReadonlyArray<Info>>`.
**Data Shape:** one DB row per resource: `{id, project_id, action, resource}` (PermissionTable); `Info` re-exported from the shared schema package.

### Decisive source
```ts
const add = Effect.fn("PermissionSaved.add")(function* (input: AddInput) {
  if (!input.resources.length) return
  yield* db
    .insert(PermissionTable)
    .values(
      input.resources.map((resource) => ({
        id: ID.create(),
        project_id: input.projectID,
        action: input.action,
        resource,
      })),
    )
    .onConflictDoNothing()
    .run()
    .pipe(Effect.orDie)
})
```
```ts
// permission.ts — saved rows re-enter evaluation as allow rules, appended AFTER configured rules:
const savedRules = EffectRuntime.fnUntraced(function* () {
  return (yield* saved.list({ projectID: location.project.id })).map(
    (item): Permission.Rule => ({ action: item.action, resource: item.resource, effect: "allow" }),
  )
})
```

**Flow:** a `reply("always")` whose request carries `save: string[]` resources inserts one row per resource (idempotent via onConflictDoNothing, empty-list no-op) → every subsequent evaluation in the same project reads the rows and projects them to `{action, resource, effect: "allow"}` rules appended after the agent's configured rules → findLast makes a saved allow beat an earlier configured ask, while the configured-deny short-circuit (checked before appending) still wins → `remove(id)` deletes one row; the permission test pins insert + list + remove round-trip.
**Invariant:** saved approvals are project-scoped (not session-scoped), row-per-resource, allow-only, and never consulted when a configured rule denies the action outright.
**Probe:** `packages/core/test/permission.test.ts` ("stores and removes saved resources for a project": DB row asserted via PermissionTable select; "uses saved bash approvals while preserving configured deny precedence": saved allow + configured deny → deny).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "opencode", query: "PermissionSaved add list PermissionTable projectID", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt persisted allow-rules as the "always allow" mechanism: row-per-resource, project-scoped, idempotent insert, projected back into the same rule engine as configured rules (never a bypass channel). Adapt the DB table and schema package to your host. Omit Drizzle/Effect specifics.
