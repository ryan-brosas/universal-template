<!-- capsule-v2 -->
# Dual pagination — cursor-first with an offset escape hatch and a hard page cap

**Source:** dub AGPL-3.0-or-later (EE dirs separately licensed) `main@873edc5a9727317513c966b8d9b9171794fc89f8`; Codebase Memory `dub`. **Question:** How do you offer stable deep listing without letting offset queries melt the database?

## buildPaginationQuery
**Path/Symbol:** `apps/web/lib/api/pagination.ts:buildPaginationQuery` (24–89).
**Signature:** `buildPaginationQuery(filters: { page?, pageSize, startingAfter?, endingBefore?, sortBy, sortOrder }): { cursor?: { id }, skip, take, orderBy }`.
**Data Shape:** two mutually exclusive modes selected by the PRESENCE of a cursor param: `startingAfter`/`endingBefore` → Prisma cursor pagination (`cursor:{id}`, `skip:1`, `take:±pageSize`); otherwise offset mode (`skip:(page-1)*pageSize`, `take:pageSize`). `MAX_OFFSET_PAGE = 1000` (:22).

### Decisive source
```ts
const useCursorPagination = !!startingAfter || !!endingBefore;
if (startingAfter && endingBefore) throw new DubApiError({ code: "unprocessable_entity", ... });
if (useCursorPagination && sortBy !== "createdAt") throw ...   // cursor ONLY on createdAt
if (useCursorPagination && page) throw ...                     // never mix modes
// cursor branch:
return { cursor: { id: startingAfter || endingBefore! },
         orderBy: { id: sortOrder },                 // tie-break order on the UNIQUE id column
         take: endingBefore ? -pageSize : pageSize,  // negative take = walk backwards
         skip: 1 };                                  // skip the cursor row itself
// offset branch (page > MAX_OFFSET_PAGE throws):
return { orderBy: { [sortBy]: sortOrder },
         take: pageSize,
         skip: (page - 1) * pageSize };
```

**Flow:** validate mutual exclusion first (both cursors / cursor+page / non-createdAt sort under cursor all reject with `unprocessable_entity`) → cursor mode walks by unique `id` with signed `take` and `skip:1` so the cursor record is excluded → offset mode caps `page ≤ 1000` and points clients at cursor mode beyond that.
**Invariant:** cursor pagination only ever orders on columns backed by a unique index (`id`, plus the fixed `createdAt` precondition), so pages are stable and cheap; the offset path is bounded (≤1000 × pageSize rows scanned worst case) instead of unbounded. Backward paging is expressed as negative `take`, not inverted sort.
**Probe:** no dedicated unit test file for pagination (vitest suites cover analytics/webhooks). Source-grounded probe: `search_graph` resolves `buildPaginationQuery`; port with your own test asserting the three rejection cases and that `endingBefore` yields negative take.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dub", query: "buildPaginationQuery MAX_OFFSET_PAGE", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt presence-of-cursor mode selection, the mutual-exclusion validations, unique-column cursor + signed take + skip-1 semantics, and the MAX_OFFSET_PAGE cap with an upgrade hint in the error; adapt the sortable column contract, the ORM query shape (Prisma here), and the cap value. Omit nothing else — this function is deliberately dependency-free apart from DubApiError. Caveat: no direct upstream test for this seam.
