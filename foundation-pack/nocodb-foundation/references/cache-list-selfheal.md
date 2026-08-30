<!-- capsule-v2 -->
# Cache list self-heal — when a cached list points at a child key that no longer exists, how does the cache repair itself instead of serving a partial list?

**Source:** nocodb (Sustainable Use License, develop branch) `develop@f7513664f3f3`; Codebase Memory project `nocodb`. **Question:** When a list's mget comes back with nulls (children evicted/TTL'd), how does the cache avoid serving half a list forever?

## NONE sentinel + missing-child deepDel fallback
**Path/Symbol:** `packages/nocodb/src/cache/CacheMgr.ts:getList` (261-389); `setList` NONE write (405-408); `appendToList` NONE reset (510-519); `deepDel` both directions (458-495).
**Signature:** `getList(scope, subKeys[], orderBy?): Promise<{list: any[]; isNoneList: boolean}>`; `setList(scope, subListKeys[], list, props[]): Promise<boolean>`; `deepDel(key, direction): Promise<boolean>`.
**Data Shape:** list key `scope[:subKey...]:list` → SET of full child keys or the literal string `'NONE'`; return contract distinguishes "empty because nothing exists" (`isNoneList`) from "empty because cache miss" (`list: []`, `isNoneList: false`) so callers know whether to hit the DB.

### Decisive source
```ts
const arr = (await this.get(key, CacheGetType.TYPE_ARRAY)) || [];
const isNoneList = arr.length && arr.includes('NONE');
if (isNoneList || !arr.length) { return { list: [], isNoneList }; }

const values = await this.client.mget(arr);
if (values.some((v) => v === null)) {
  // FALLBACK: a key is missing from list, this should never happen
  logger.error(`${this.context}::getList: missing value for ${key}`);
  const allParents = [];
  values.forEach((v) => {           // rebuild parents from surviving children
    if (v) { const o = JSON.parse(v); allParents.push(...this.getParents(o)); }
  });
  const uniqueParents = [...new Set(allParents)];
  await Promise.all(uniqueParents.map((p) => this.deepDel(p, CacheDelDirection.PARENT_TO_CHILD)));
  return { list: [], isNoneList };
}
// setList on an empty list stores the NONE marker instead of an empty set
if (!list.length) { return this.set(listKey, ['NONE']); }
```

**Flow:** read list SET → `mget` children → any null ⇒ treat the whole structure as corrupt, collect every parent key still referenced by surviving children, and PARENT_TO_CHILD-deepDel each — the next read repopulates from source of truth. `appendToList` hitting `'NONE'` deletes the marker first so real appends start a fresh SET.
**Invariant:** never serve a partially-missing list — one null in `mget` poisons the entire list. The `'NONE'` sentinel must be stored as a SET member (not absent key) to cache "definitely empty" and skip repeated DB hits; callers use `isNoneList` to decide DB fallback.
**Probe:** no unit test upstream. Source-grounded probe: `CacheMgr.ts:295-328` — the `values.some(v => v === null)` branch ends in deepDel of every unique parent, not partial return; `:512-519` — appendToList clears NONE before pushing.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "CacheMgr getList setList deepDel NONE", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the poison-list self-heal (null ⇒ delete parents, rebuild next read), the NONE empty-marker, and the two-sided empty contract; adapt scope/key construction and direction enum names to host; omit orderBy sugar. Coverage caveat: no in-repo tests; source-grounded.
