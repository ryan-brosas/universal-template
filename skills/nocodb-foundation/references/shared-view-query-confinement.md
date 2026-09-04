<!-- capsule-v2 -->
# Shared-view query confinement — how does an anonymous caller get stopped from using where/sort/fields as a read oracle for hidden columns?

**Source:** NocoDB Sustainable Use License `develop@f7513664`; Codebase Memory `nocodb`. **Question:** The payload always hides view-hidden columns — so how must the QUERY surface (where/sort/filterArr/fields) also be confined, per leaf, without breaking multi-field search?

## restrictSharedViewQuery + scope hoisting
**Path/Symbol:** `packages/nocodb/src/helpers/sharedViewQueryHelpers.ts:restrictSharedViewQuery` (:86-204), `resolveSharedViewQueryScope` (:56-68), `restrictSharedViewColumnReferences` (:246-322); consumer matrix in `packages/nocodb/src/services/public-datas.service.ts` DESIGN NOTE (:82-114).
**Signature:** `async restrictSharedViewQuery(context, { model, view?, query /* mutated in place */, scope? }): Promise<void>`.
**Data Shape:** `scope = { exposedColumnIds: Set<colId>, columns, aliasColObjMap }` — resolvable ONCE and reused across N bulk entries. SANITIZED_QUERY_KEYS spreads `LIST_ARG_ALIAS_KEYS` (canonical + short aliases w/f/s/filters) plus filterArr(Json)/sortArr(Json).

### Decisive source
```ts
// Query keys `restrictSharedViewQuery` can rewrite.
// ... enumerating the canonical names here once left `?w=(Secret,eq,x)` compiling
// against the model's full `aliasColObjMap`, i.e. the gate open.
const SANITIZED_QUERY_KEYS = [...LIST_ARG_ALIAS_KEYS, 'filterArrJson', 'filterArr', 'sortArrJson', 'sortArr'];
```
```ts
if (!query || !view || !isSharedViewAccess(context)) return;
// Skip the column/view resolution: this runs on every public list/count request
if (!SANITIZED_QUERY_KEYS.some((key) => query[key])) return;
...
// `fields` (and its `f` alias) — CE's list path ignores caller fields ..., but the EE
// optimized path forwards them and `sanitizePublicQuery` does not strip them.
// Intersect rather than drop, so a projection naming only shown columns still works.
const kept = requested.filter((ref) => {
  const colId = aliasColObjMap[ref]?.id ?? ref;
  // Unresolvable names are harmless downstream — keep them.
  return !columns.some((c) => c.id === colId) || exposedColumnIds.has(colId);
});
```

**Flow:** gate ONLY on access SOURCE (`isSharedViewAccess`) — never `context.is_public`, because a shared base is an authenticated pseudo-user whose query surface stays unrestricted → cheap key-presence short-circuit BEFORE any column/view resolution (hot anonymous path) → restrictQueryToExposedColumns strips where/sort PER LEAF/TERM (multi-field searches degrade to their visible terms instead of failing or widening) → filterArr trees stripped per fk_column_id entry (string form re-serialized; all-hidden ⇒ undefined) → fields INTERSECTED with exposed ids (unresolvable names kept — harmless downstream) → sortArr entries dropped when their field resolves to an unexposed colId.
**Invariant:** (1) Strip-don't-reject everywhere EXCEPT group-by, where the column IS the answer (that one 4xxes via assertSharedViewGroupByColumn). (2) Key enumeration MUST include aliases or the gate is open — upstream recorded the exact bypass incident in the comment. (3) The function MUTATES the caller's query; data fetch AND count both compile from it afterwards. (4) Bulk routes resolve scope once and pass it per-entry (bulkAggregate sanitizes each entry BEFORE confining because sanitize copies while restrict mutates).
**Probe:** No runner at this pin — deterministic probes: search_graph resolves `helpers.sharedViewQueryHelpers.restrictSharedViewQuery` :86-204 exactly; grep confirms LIST_ARG_ALIAS_KEYS spread is the only alias source and the DESIGN NOTE names its CVEs (CVE-2026-47378 / CVE-2026-47279 / GHSA-qqxm-7cj9-5fr2).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "restrictSharedViewQuery exposedColumnIds LIST_ARG_ALIAS_KEYS", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt access-source gating, alias-complete key enumeration, strip-per-term semantics, and scope hoisting for bulk entries. Adapt the key vocabulary to your list-args surface. Omit the aggregation branch if your host has no raw-value aggregate endpoint.
