<!-- capsule-v2 -->
# RLS filter tree — why enforcement must link rows into an in-memory tree instead of re-reading children after substitution

**Source:** NocoDB Sustainable Use License `develop@f7513664f3f3b7286023a7e832a8333808f7557b`; Codebase Memory project `nocodb`. **Question:** When porting row-level-security filter application, why does a helper exist to rebuild parent→children in memory, and what breaks if you reuse the flat root-list + lazy-`getChildren` pattern the rest of the model uses?

## In-memory tree linking (`linkFilterRowsIntoTree`)
**Path/Symbol:** `packages/nocodb/src/models/Filter.ts:linkFilterRowsIntoTree` (:44-70), consumed only by `Filter.rootFilterTreeByRlsPolicy` (:1188-1202) over `filterObjsByRlsPolicy` (:1123-1156).
**Signature:** `export function linkFilterRowsIntoTree<T extends { id?: string; fk_parent_id?: string; children?: T[] }>(rows: T[]): T[]`.
**Data Shape:** Input: flat FILTER_EXP rows (roots = rows with falsy `fk_parent_id`). Output: roots array with `children` populated recursively. No depth cap BY DESIGN.

### Decisive source
```ts
// packages/nocodb/src/models/Filter.ts:27-42 (comment is the contract)
/**
 * No depth cap on purpose. A cap would silently drop the conditions below it,
 * and for RLS a dropped condition is not a narrower filter — an unpopulated
 * `children` makes `getChildren()` fall through and reload the raw rows from
 * cache, undoing any substitution already applied to them. Truncating here
 * fails *open*.
 *
 * It also isn't needed: every row has exactly one `fk_parent_id` and the walk
 * starts only at rows that have none, so each row is reached at most once ...
 * Rows in a `fk_parent_id` cycle have no root in their component and are
 * therefore never reached at all.
 */
```
And the consumer-side trap it prevents (`:1177-1187`, on `rootFilterTreeByRlsPolicy`):
```ts
// RLS enforcement must use this, not `rootFilterListByRlsPolicy`. That one
// returns root rows with `children` unset, so `getChildren` reloads them
// straight from the cache *after* `resolveRlsDynamicValues` has run — a
// placeholder nested inside a filter group would never be substituted and
// would reach SQL as literal `{currentUser.x}` text. Under a negated
// operator that literal inverts into a match-everything clause.
```

**Flow:** load ALL policy rows flat (cache list `[RLS_POLICY, id]`, order asc) → `castType` each → `linkFilterRowsIntoTree` attaches children by single-parent walk from roots → caller substitutes dynamic values over the WHOLE tree first → `getChildren()` short-circuits on already-set `children` (`:617`) so substituted children are the ones compiled into SQL.
**Invariant:** RLS conditions must fail CLOSED: never let a nested condition be re-fetched post-substitution, never truncate depth (a dropped RLS condition widens access, not narrows it); cycles are unreachable-by-construction so no visited-set is needed.
**Probe:** No direct unit test exists for these symbols at this pin (grep over `packages/nocodb/src/**` finds zero spec references). Deterministic probe: `search_graph --project nocodb --query 'rootFilterTreeByRlsPolicy'` resolves `Filter.rootFilterTreeByRlsPolicy … Filter.ts 1188-1202`; source lines above verified verbatim by direct read.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "linkFilterRowsIntoTree rootFilterTreeByRlsPolicy", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the fail-closed doctrine (resolve-then-link whole tree before compile; unpopulated `children` after value substitution = security bug) and the cycle-safety argument that makes a depth cap unnecessary. Adapt the generic `<T>` signature to your host's row shape. Omit nothing portable here — the CE `BaseModelSqlv2.getRlsConditions()` override point (`packages/nocodb/src/db/BaseModelSqlv2.ts:10307-10317`, memoized promise + `cloneFilters()` deep copy per read :230-238 so one query's normalization can't reach the next) is the injection seam an EE host would implement. Coverage caveat: EE policy-resolution body lives outside this CE pin; probes are deterministic graph+source, no runner.
