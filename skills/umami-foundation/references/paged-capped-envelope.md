<!-- capsule-v2 -->
# Capped pagination envelope — how do you paginate expensive analytics queries with an honest "isCapped" flag instead of counting everything?

**Source:** umami v3.3.1 / MIT @ master`ca661c70`; Codebase Memory `ext-umami`. **Question:** How does paging work identically over ClickHouse and Postgres raw SQL, including the maxResults cap?

## paged-capped-envelope
**Path/Symbol:** `src/lib/clickhouse.ts:pagedRawQuery :636-671`; twin `src/lib/prisma.ts:pagedRawQuery :784-818`, `pagedQuery :761-782`.
**Signature:** `(query, queryParams, filters{page,pageSize,orderBy,sortDescending,search,maxResults}) -> { data, count, page, pageSize, orderBy?, search?, isCapped }`.
**Data Shape:** `count` = capped count when `maxResults` set: `select count(*) from (select 1 from (<query>) t limit <maxResults>) t2`.

### Decisive source
```ts
const statements = [
  orderBy && `order by ${orderBy} ${direction}`,
  +size > 0 && `limit ${+size} offset ${+offset}`,
].filter(n => n).join('\n');
const countQuery = maxResults
  ? `select count(*) as num from (select 1 from (${query}) t limit ${+maxResults}) t2`
  : `select count(*) as num from (${query}) t`;
const count = await rawQuery(countQuery, queryParams).then(res => res[0].num);
...
isCapped: !!maxResults && +count >= +maxResults,
```

**Flow:** run COUNT first (cheap under cap), then the page slice — two queries, same params. `isCapped=true` tells the UI there are at least maxResults rows without proving an exact total.
**Invariant:** numeric coercion (`+size`) happens BEFORE string interpolation of limit/offset; orderBy is still interpolated raw — it comes from a validated enum upstream (`fieldsParam`), NOT user text; preserve that pairing or you open injection. The prisma twin returns `Number(res[0].num)` because pg drivers return bigint-as-string — CH returns number already.
**Probe:** no direct unit test for pagedRawQuery (coverage caveat: thin wrapper); structural pins: `grep -c "isCapped" src/lib/clickhouse.ts src/lib/prisma.ts | awk -F: '{s+=$2} END{print s}'` → ≥2.
**Probe:** `grep -n "select count(\*) as num" src/lib/clickhouse.ts src/lib/prisma.ts` → one line each.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-umami", query: "pagedRawQuery maxResults isCapped", limit: 10 });
```

## Verdict
Adopt capped-count pagination for any heavy-scan listing API; adapt default page size and cap values; omit prisma findMany variant if fully on raw SQL.
