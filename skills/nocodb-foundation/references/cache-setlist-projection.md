<!-- capsule-v2 -->
|# Cache setList projection — projected child keying and dual-gate write suppression

**Source:** nocodb (Sustainable Use License, develop branch) `develop@f751366`; Codebase Memory project `nocodb`. **Question:** When a model caches a LIST (not a single object), how are per-item keys derived — and which gates does the write respect?

## Path/Symbol
`packages/nocodb/src/cache/NocoCache.ts:setList` (162–176); canonical consumer `models/BaseUser.ts:315-323`; read twin `getList` + `isNoneList` sentinel (cache-list-selfheal.md).

**Signature:** `static async setList(context, scope, subListKeys: string[], list: any[], props: string[] = []): Promise<boolean>`.

**Data Shape:** each item stored as `${prefix}:${ctx}:${scope}:${subListKeys.join(':')}:${item[props[0]]}:${item[props[1]]}...` and registered in a parent SET under the subListKeys prefix; `props` names the fields forming each child key, positionally ordered.

### Decisive source
```ts
public static async setList(context, scope, subListKeys, list, props = []) {
  if (this.cacheDisabled || isCacheBypassed()) return Promise.resolve(true);
  return this.client.setList(
    `${this.prefix}:${cacheContext(context)}:${scope}`,
    subListKeys, list, props,
  );
}
// consumer:
if (!strict_in_record) {
  await NocoCache.setList(context, CacheScope.BASE_USER, [base_id], baseUsers, ['base_id', 'id']);
}
```

**Flow:** model builds list → enrich rows → setList writes one child per item keyed by projected props + appends children to the scope SET → later getList([base_id]) returns children; deepDel on any child poisons → self-heal rebuilds (cache-list-selfheal.md).

**Invariant:** (1) Projected props MUST exist on every item or child keys collide on `undefined` — BaseUser stamps `base_id` onto rows precisely because the JOIN may leave it null. (2) The write respects BOTH gates (disabled + isCacheBypassed): transactional scopes never cache mid-flight state. (3) Query-shaped reads (`strict_in_record`) skip write-back entirely — they must never seed the canonical cache. (4) props array is positional; order defines the key path.

**Probe:** no unit test upstream. Source-grounded probe: NocoCache.ts:162-176 whole method, :169 dual-gate line, BaseUser.ts:306-323 stamp-then-setList sequence, pairing capsules cache-envelope.md / cache-list-selfheal.md / cache-gate-matrix.md.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "NocoCache setList getList isNoneList cacheDisabled isCacheBypassed", limit: 8, fields: ["signature","name","file"] });
```

## Verdict
Adopt projected-prop child keying with dual-gate suppression and query-shaped-read opt-outs; adapt scope naming; omit nothing. Coverage caveat: no in-repo unit tests; source-grounded.
