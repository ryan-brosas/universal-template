<!-- capsule-v2 -->
# Customers list kernel + three-member cursor-identity family — how does a list endpoint validate a cursor, and what does the customers where-builder add over the links plane?

**Source:** dub AGPL-3.0-or-later `main@29df217a2963`; Codebase Memory `dub`. **Question:** Beyond buildPaginationQuery's mode selection (dual-pagination), what does the customers list endpoint itself verify about a cursor — and which of the platform's list kernels share that check?

## Connected graph-selected seam
**Path/Symbol:** `apps/web/lib/customers/api/get-customers.ts:getCustomers` (:11-115) · family members `apps/web/lib/api/links/get-links-for-workspace.ts` (:48-67) and `apps/web/lib/api/commissions/get-commissions.ts:getCommissions` (:42-62) · `apps/web/lib/api/pagination.ts:buildPaginationQuery` (:17-89) · route `apps/web/app/(ee)/api/customers/route.ts:GET` (:23-54) · schema `apps/web/lib/zod/schemas/customers.ts` (:12, :17-77).
**Signature:** `getCustomers(filters: GetCustomersInput): Promise<Customer & relations?>` — cursor block runs BEFORE the findMany; route pins programId before calling.
**Data Shape:** cursors are raw row ids; `customerIds` accepts string OR array (transform splits ","); `includeExpandedFields` boolean toggles the include; pageSize default 100 (CUSTOMERS_MAX_PAGE_SIZE).

### Decisive source
```ts
// THE FAMILY (3 members, byte-identical message + code; scope column adapts per resource)
// get-customers.ts :29-49  /  get-links-for-workspace.ts :48-67  /  get-commissions.ts :42-62
const cursorId = startingAfter || endingBefore;
if (cursorId) {
  const customer = await prisma.customer.findUnique({
    where: { id: cursorId }, select: { id: true, projectId: true } });
  if (!customer || customer.projectId !== workspaceId) {   // commissions checks programId !== programId instead
    throw new DubApiError({ code: "unprocessable_entity",
      message: "Invalid cursor: the provided ID does not exist." });  // uniform: missing AND foreign are indistinguishable
  }
}
```
```ts
// pagination.ts — cursor mode FORCES id ordering; offset mode honors [sortBy] (the comment above it is STALE)
if (useCursorPagination) {
  return { cursor: { id: cursorId }, orderBy: { id: sortOrder },
           take: endingBefore ? -pageSize : pageSize, skip: 1 };
}
...
return {
  // Order by id only for better query performance on large datasets (single-column PK index).   ← STALE: contradicts the code below
  // Trade-off: ordering is by id rather than createdAt, so order may not strictly match creation time.
  orderBy: { [sortBy]: sortOrder },        // :83-85 — offset mode DOES honor sortBy (createdAt/saleAmount/firstSaleAt/subscriptionCanceledAt for customers)
  take: pageSize, skip: (page - 1) * pageSize };
```
```ts
// get-customers.ts :65-76 identity ladder + :85-113 conditional include
...(email ? { email } : externalId ? { externalId }
  : search ? search.includes("@") ? { email: search }
           : { email: { search: sanitizeFullTextSearch(search) }, name: { search: sanitizeFullTextSearch(search) } }
  : {}),
...paginationQuery,
...(includeExpandedFields ? { include: {
    link: { select: { id, domain, key, shortLink, url, programId } },
    programEnrollment: { include: { partner: { select: { id, name, email, image } }, discount: true } },
} } : {}),
```
**Flow:** route parses Extended schema → pins programId via getDefaultProgramIdOrThrow when programId||partnerId present (:29-31) → getCustomers validates cursor IDENTITY (exists ∧ in-scope, one uniform 422) → findMany with tenancy-flat where + identity ladder → route switches response schema on includeExpandedFields (CustomerSchema vs CustomerEnrichedSchema.extend({discount: DiscountSchemaWithDeprecatedFields}) — the deprecated-field overlay lives on the ROUTE, not the lib, :39-43).
**Invariant:** (1) The pre-query cursor identity check is a THREE-member family (links/customers/commissions) with ONE uniform message and ONE code (unprocessable_entity) — missing and foreign cursors are deliberately indistinguishable (no existence oracle); only the scope column adapts (projectId vs programId). The pass-15 note's claim that "links used not_found" is REFUTED by source (get-links-for-workspace.ts :63 uses unprocessable_entity). (2) Cursor mode orders by id with skip:1 and negative take for endingBefore; offset mode honors [sortBy] — the "Order by id only" comment in pagination.ts is stale and must not be ported. (3) Expanded fields are an opt-in INCLUDE, never a default join: the base list stays a single-table query, and the enriched exit shape is enforced by a different zod schema chosen at the route boundary.
**Probe:** No direct test for the customers list route (tests/**/*customer* ∅). Deterministic probes executed at pin: `Invalid cursor: the provided ID does not exist.` census = exactly 3 sites (get-customers.ts:46, get-commissions.ts:59, get-links-for-workspace.ts:64), all with `code: "unprocessable_entity"`; `orderBy: { [sortBy]: sortOrder }` at pagination.ts:84 directly under the stale comment; `CUSTOMERS_MAX_PAGE_SIZE = 100` at schemas/customers.ts:12 (platform default — links/commissions/partners/groups/payouts all 100).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dub", query: "getCustomers startingAfter endingBefore cursor", limit: 5 }); // rank-1 expected: get-customers.ts
await mcp.codebase_memory.search_graph({ project: "dub", query: "buildPaginationQuery MAX_OFFSET_PAGE skip 1 negative take", limit: 5 }); // pagination kernel
```

## Verdict
Adopt the three-member pattern: resolve the cursor row and assert scope BEFORE paging, with one uniform error for missing-vs-foreign, and let the scope column follow the resource's tenancy key. Adopt the id-ordered/skip:1/negative-take cursor branch and the [sortBy]-honoring offset branch (ignore stale comments about index strategy). Adapt the include-expanded-fields toggle to your relation set, and keep the response-schema switch at the route boundary. Omit the deprecated offset page entirely if you can require cursors. Caveat: no direct test exists for the customers list plane; anchors are line-pinned at the pin.
