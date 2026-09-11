<!-- capsule-v2 -->
# command-palette base list — how is the user's base roster cached so command-palette cleanup piggybacks for free?

**Source:** nocodb (Sustainable Use License) `develop@640fe3b06fb26c9d000e2258477001c0d5e62c73`; Codebase Memory `mnt-hdd-utopia-inspo-platforms-nocodb`. **Question:** What shape does baseListAll return, which roles are excluded, and how does its cache key join the existing cleanup lists?

## command-palette base list
**Path/Symbol:** `packages/nocodb/src/helpers/baseListAllHelpers.ts` — whole file 78L: `getBaseListAll` (:24–78), interface `BaseListAllResult` (:7–22); consumer `controllers/internal/modules/BaseListAllGet.operations.ts` (PAT filtering on top).
**Signature:** `getBaseListAll(userId: string, ncMeta = Noco.ncMeta) → Promise<BaseListAllResult>`.
**Data Shape:** cache key `${CacheScope.CMD_PALETTE}:baseListAll:${userId}` under scope 'root'; result wraps bases in a SINGLE synthetic workspace `{id:'nc', title:'NocoDB', meta:{}, bases}`.

### Decisive source
```ts
// :33–48 — the roster query:
const rows = await ncMeta
  .knexConnection(`${MetaTable.PROJECT} as b`)
  .select('b.id as base_id', 'b.title as base_title', 'b.meta as base_meta',
          'bu.roles as base_role', 'b.order as base_order')
  .innerJoin(`${MetaTable.PROJECT_USERS} as bu`, `b.id`, `bu.base_id`)
  .where('bu.fk_user_id', userId)
  .andWhereNot('bu.roles', ProjectRoles.NO_ACCESS)
  .andWhere(function () {
    this.where('b.deleted', false).orWhereNull('b.deleted');
  })
  .orderBy('b.order', 'asc');
// :69–74 — piggyback registration:
await NocoCache.set('root', key, cached);
// Append to the same lists command palette uses so cleanup piggybacks
await NocoCache.set('root', `${CacheScope.CMD_PALETTE}:ws`, [key]);
await NocoCache.set('root', `${CacheScope.CMD_PALETTE}:user:${userId}`, [key]);
```

**Flow:** cache read → miss: join project×project_users filtered by user + role≠NO_ACCESS + not-deleted → map with parseMetaProp → wrap in one fake workspace → cache write PLUS registering the key into the ws-list and per-user-list entries that command palette invalidation already walks.
**Invariant:** The piggyback list-append means NO dedicated eviction logic exists or is needed — any palette-role/membership change clears both consumers together. Roles column is a raw string on PROJECT_USERS (single-role-per-row storage). The PAT filter in the operations layer POST-FILTERS the cached result (Set membership) rather than bypassing cache — scoped tokens see a subset of the same envelope.
**Probe:** `grep -c "CMD_PALETTE}:ws" packages/nocodb/src/helpers/baseListAllHelpers.ts` → `1`; `grep -c "NO_ACCESS" packages/nocodb/src/helpers/baseListAllHelpers.ts` → `1`.
**Coverage caveat:** grep-derived; only controller-existence specs exist (`command-palette.controller.spec.ts`, `should be defined`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-nocodb", query: "getBaseListAll CMD_PALETTE baseListAll", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt single-workspace envelope, NO_ACCESS exclusion, soft-delete OR-null clause, and the piggyback list-registration pattern as the port's cache-cleanup strategy; adapt CacheScope names.
