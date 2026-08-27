<!-- capsule-v2 -->
# Customer count-where builder — why must a grouped COUNT drop the filter on the dimension it groups by?

**Source:** dub AGPL-3.0-or-later `main@29df217a2963`; Codebase Memory `dub`. **Question:** When one endpoint serves both identity lookups and groupBy badges, what does the count-side where-builder carry that the list-side twin deliberately does not?

## Connected graph-selected seam
**Path/Symbol:** `apps/web/lib/customers/api/customer-count-where.ts:buildCustomerCountWhere` (:10-56); list twin `apps/web/lib/customers/api/get-customers.ts:getCustomers` (:11-115).
**Signature:** `buildCustomerCountWhere(filters: z.infer<getCustomersCountQuerySchema> & { workspaceId }) => Prisma.CustomerWhereInput`.
**Data Shape:** In: programId?, partnerId?, workspaceId, email? | externalId? | search?, country?, linkId?, groupBy?. Callers (trace inbound depth 1): `app/(ee)/api/customers/count` and `app/(ee)/api/customers/export` routes ONLY.

### Decisive source
```ts
// identical identity ladder to the list builder — but SEPARATE COPY:
...(email ? { email }
  : externalId ? { externalId }
  : search
    ? search.includes("@")
      ? { email: search }                                        // @ ⇒ exact-email match
      : { email: { search: sanitizeFullTextSearch(search) },
          name:  { search: sanitizeFullTextSearch(search) } }    // else MySQL full-text email+name
    : {}),
// only filter by country if not grouping by country
...(country && groupBy !== "country" && { country }),            // :44-47 SELF-EXCLUSION
// only filter by linkId if not grouping by linkId
...(linkId && groupBy !== "linkId" && { linkId }),               // :49-52
```
List twin (`get-customers.ts` :65-82) repeats the ladder verbatim but filters `country`/`linkId` UNCONDITIONALLY — a list never groups, so it never needs the guard.
**Flow:** route parses count query → builder folds tenancy (`projectId: workspaceId`) + optional program/partner scope → identity resolution picks AT MOST ONE of exact-email / externalId / full-text search → dimension filters survive only when they are not the grouping axis → caller runs prisma.customer.groupBy/count.
**Invariant:** You cannot constrain a grouped count by its own grouping dimension: filtering `country:"US"` while grouping by country would zero every other bucket and make the badge chart lie. The exclusion lives in the WHERE-BUILDER (not the route) so every count consumer inherits it. The identity ladder is duplicated between count and list builders rather than shared — port as one grammar with two copies or extract consciously.
**Probe:** No direct test for this builder (glob tests/**/*customer* = ∅ this run). Census probe executed live: pattern `groupBy !== ` = 23 matches in 12 source files (api-logs-count ×3, network/programs/count ×3, get-links-count ×3, earnings/count ×3, referrals/count ×2, customers/count ×2 [partner-profile], customer-count-where ×2, links/count folderId, admin/links/count domain, submitted-leads counts ×2, programs submitted-leads/count ×1) — a platform-wide count grammar, not a local trick.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dub", query: "buildCustomerCountWhere customer count where groupBy", limit: 10 }); // rank-1 :10-56
await mcp.codebase_memory.trace_path({ project: "dub", function_name: "buildCustomerCountWhere", direction: "inbound", depth: 1 });   // callers_total=2: count + export routes
```

## Verdict
Adopt dimension-self-exclusion as a hard rule of any grouped-count API, implemented inside the shared where-builder. Adapt the identity ladder ordering (email beats externalId beats search) to your identity model. Omit nothing silently: dropping the guard corrupts every groupBy badge downstream.
