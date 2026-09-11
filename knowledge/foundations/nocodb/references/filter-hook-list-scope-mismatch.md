<!-- capsule-v2 -->
# rootFilterListByHook — a live read/write cache-scope mismatch inside Filter.ts itself

**Source:** NocoDB Sustainable Use License `develop@f7513664f3f3b7286023a7e832a8333808f7557b`; Codebase Memory project `nocodb`. **Question:** If you port the hook-filter read path by copying `rootFilterListByHook`, what latent bug travels with it — and which callers currently absorb it?

## The mismatched twin of parentFilterListByHook
**Path/Symbol:** `packages/nocodb/src/models/Filter.ts:Filter.rootFilterListByHook` (:1085-1120); contrast `parentFilterListByHook` (:1283-1327).
**Signature:** `static async rootFilterListByHook(context: NcContext, { hookId }: { hookId: string }, ncMeta = Noco.ncMeta): Promise<Filter[]>`.
**Data Shape:** reads/writes NocoCache lists under `CacheScope.FILTER_EXP`; returns root rows (`!f.fk_parent_id`) cast to Filter.

### Decisive source
```ts
// packages/nocodb/src/models/Filter.ts:1090-1094 — READS the VIEW-scoped list key
const cachedList = await NocoCache.getList(
  context,
  CacheScope.FILTER_EXP,
  [FilterCacheScope.VIEW, hookId],      // <-- scope says VIEW, id is a HOOK id
  { key: 'order' },
);
// ...
// :1110-1114 — but WRITES the HOOK-scoped list key
await NocoCache.setList(
  context,
  CacheScope.FILTER_EXP,
  [FilterCacheScope.HOOK, hookId],      // <-- correct scope on write only
  filterObjs,
);
```
Callers that keep this from corrupting views today (all re-read after writes, or bypass cache):
- `packages/nocodb/src/models/Hook.ts:117` (`getFilters`)
- `packages/nocodb/src/services/filters.service.ts:66` (`hookFilterList`)
- `packages/nocodb/src/services/hooks.service.ts:154,303` (snapshot walk + delete-then-reinsert update flow)

**Flow:** getList(VIEW-scoped, hookId) → miss ⇒ DB query correctly keyed `fk_hook_id` → setList(HOOK-scoped, hookId) → filter roots. The DB result is always correct; only the cache keys disagree.
**Invariant (the porting lesson):** the source of truth is always the DB condition; a wrong list-scope key degrades to repeated misses + redundant setLists, NOT stale data — as long as every mutation path evicts/rebuilds both scopes and no caller trusts the mis-keyed read. Porters must NOT copy the read key; they must also not "fix" it silently if their consumers rely on miss-always behavior.
**Probe:** No direct unit test at this pin. Deterministic probes: verbatim grep `[FilterCacheScope.VIEW, hookId]` unique to :1093 in Filter.ts; sibling verbatim `[FilterCacheScope.HOOK, hookId]` at :1030/:1036 (`allHookFilterList`) and :1113; all four call sites resolve via search_graph (`rootFilterListByHook`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "rootFilterListByHook FilterCacheScope.HOOK", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt: nothing of the mismatch — adopt its LESSON: derive list-cache scope keys mechanically from the same expression used for the DB condition, and treat any read/write scope divergence as a bug class to grep for when porting cache-projection layers. Adapt by fixing the read key in your port (and note upstream may patch it later — diff-driven re-entry should check this line first). Omit: none. Coverage caveat: line-pinned source + graph probes; no runner at this pin.
