<!-- capsule-v2 -->
# Count badge groupBy grammar — what is the platform-wide shape of grouped-count endpoints, and where do the members diverge?

**Source:** dub AGPL-3.0-or-later `main@29df217a2963`; Codebase Memory `dub`. **Question:** When one endpoint serves both a total badge and per-dimension breakdowns, what grammar do all the count routes share — and which member-specific divergences (pivot, hydration tolerance, privacy, response shape) must a porter decide deliberately?

## Connected graph-selected seam
**Path/Symbol:** `apps/web/app/(ee)/api/partner-profile/programs/[programId]/referrals/count/route.ts:GET` (:10-80) · `.../customers/count/route.ts:GET` (:15-133) · `.../earnings/count/route.ts:GET` (:12-130) · workspace twin `apps/web/app/(ee)/api/customers/count/route.ts:GET` (:9-85) · extracted builder `apps/web/lib/customers/api/customer-count-where.ts:buildCustomerCountWhere` (:10-56).
**Signature:** all `GET` under `withPartnerProfile`/`withWorkspace`; query schemas carry `groupBy?` plus the dimension filters (country/status/linkId/customerId).
**Data Shape:** groupBy arm → `prisma.<model>.groupBy({ by: [dim], where, _count: true, orderBy: { _count: { [dim]: "desc" } } })`; default arm → plain `count(where)`.

### Decisive source
```ts
// THE GRAMMAR (inline form, referrals/count :29-42): gate → self-exclusion where → three-arm switch
const baseWhere = { programId, applicationEvent: { referredByPartnerId: partner.id },
  ...(country && groupBy !== "country" && { partner: { country } }),   // SELF-EXCLUSION
  ...(status  && groupBy !== "status"  && { status }), };
if (groupBy === "status")  return NextResponse.json(await prisma.programEnrollment.groupBy({ by: ["status"], where: baseWhere, _count: true }));
if (groupBy === "country") return NextResponse.json(await prisma.partner.groupBy({          // PIVOT: dimension lives on the RELATED model
  by: ["country"], where: { country: { not: null }, programs: { some: baseWhere } },         // :54-72
  _count: true, orderBy: { _count: { country: "desc" } } }));
return NextResponse.json(await prisma.programEnrollment.count({ where: baseWhere }));        // bare number
```
```ts
// earnings/count — dynamic dimension + per-row privacy + KEPT hydration misses:
let counts = await prisma.commission.groupBy({ by: [groupBy], where: { ...where,
  ...(status && groupBy !== "status" && { status }), ...(linkId && groupBy !== "linkId" && { linkId }),
  ...(customerId && groupBy !== "customerId" && { customerId }) }, _count: true, orderBy: { _count: { [groupBy]: "desc" } } });  // :56-70
// customerId arm: obfuscate UNLESS the sharing flag is set; missing customer ⇒ synthetic name, row KEPT:
email: customer?.email ? (customerDataSharingEnabledAt ? customer.email : obfuscateCustomerEmail(customer.email))
                       : customer?.name || generateRandomName(),                              // :102-113
// default arm returns an OBJECT, not a bare number:
return NextResponse.json({ count });                                                        // :127
```
```ts
// customers/count (partner + workspace twins) — linkId arm is BOUNDED and DROPS misses:
take: 10000,                                                                                // :93 partner / :51 workspace
const enrichedData = data.map((d) => { const link = links.find(...); if (!link) return null; return {...d, domain: link.domain, ...}; }).filter(Boolean);  // DROPS vanished links
```
```ts
// workspace customers/count — ADVERTISED-ENUM-vs-IMPLEMENTED-ARMS divergence (pass-17 correction):
// schema advertises THREE arms (lib/zod/schemas/customers.ts :99):
.extend({ groupBy: z.enum(["country", "linkId", "partnerId"]).optional() });
// route implements ONLY two (app/(ee)/api/customers/count/route.ts):
if (groupBy === "country") { ... }   // :25
if (groupBy === "linkId")  { ... }   // :41
const count = await prisma.customer.count({ where: commonWhere });  // :80 ← groupBy=partnerId SILENTLY lands here (plain total)
// partnerId appears in the route ONLY as the program-pinning trigger (:14-16), never as a grouping arm
```
**Flow:** parse `{groupBy?, <dimension filters>}` → apply route gate (referralRewardId / LARGE_PROGRAM / plan) → build where with each dimension filter dropped when it equals the grouping axis → switch: named groupBy arms run `groupBy` with `_count` ordered desc (plus optional bounded hydration), default arm runs plain `count`. The workspace customers twin delegates the self-exclusion to `buildCustomerCountWhere` (the extracted-builder form, see customer-count-groupby-self-exclusion); the partner-profile routes keep it inline.
**Invariant:** (1) A grouped count must never filter on its own grouping dimension — every member enforces this, either inline (`groupBy !== "<dim>"`, census: 2+2+3 occurrences across the three partner-profile routes) or in the shared builder. (2) Members diverge on SIX deliberate axes a porter must choose: **pivot** (referrals' country arm queries the related `partner` table via `programs: { some: baseWhere }` because the dimension lives there), **hydration tolerance** (customers/count DROPS rows whose link vanished via `.filter(Boolean)`; earnings/count KEEPS them with undefined fields), **privacy** (earnings/count obfuscates emails per-row inside badge responses unless `customerDataSharingEnabledAt`; customers/count instead gates SEARCH behind that flag), **response shape** (bare number vs `{count}` object), **bounding** (linkId arms cap at `take: 10000`), and **advertised-enum-vs-implemented-arms** (the workspace customers/count query schema advertises `groupBy` enum `["country","linkId","partnerId"]` at schemas/customers.ts :99 but the route implements only the country (:25) and linkId (:41) arms — `groupBy=partnerId` SILENTLY falls through to the plain total count (:80); an unimplemented advertised dimension is an undocumented API behavior, not a bug in the grammar). (3) NO member zero-fills: unlike the payout-count-eligibility ancestor (enum zero-fill for stable tabs), these badges return only non-empty buckets ordered by `_count` desc — clients must tolerate empty breakdowns.
**Probe:** No direct tests for any of the four count routes. Deterministic probes executed at pin: `groupBy !==` counts = 2 (referrals) / 2 (partner customers) / 3 (earnings) / 0 (workspace count — delegated to builder) / 2 (builder); NEGATIVE probe: `LARGE_PROGRAM_IDS` absent from earnings/count (0 matches — the large-program gate does NOT apply to earnings badges); `filter(Boolean)` present at partner customers/count :121 and workspace count :75, ABSENT from earnings/count; `obfuscateCustomerEmail` at earnings/count :109; `some: baseWhere` pivot at referrals/count :60; pass-17 correction probe (re-executed at pin): `groupBy === "partnerId"` ABSENT from workspace customers/count route (0 matches — the schema-advertised partnerId arm has no implementation; only country :25 / linkId :41 arms exist, fallthrough to plain count at :80) while `z.enum(["country", "linkId", "partnerId"])` IS present at schemas/customers.ts :99.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dub", qn_pattern: ".*/count/route\.ts$", name_pattern: "^GET$", limit: 20 }); // platform count-route census
await mcp.codebase_memory.search_graph({ project: "dub", query: "groupBy _count orderBy _count desc badge count self-exclusion", limit: 10 }); // rank-1 expected: one of the three partner-profile count routes
```

## Verdict
Adopt the three-arm grammar (gate → self-excluding where → groupBy/count switch) as the standard badge-count shape, and make the six divergence axes EXPLICIT decisions per endpoint: where the dimension physically lives (same-table vs pivot), whether vanished join targets drop or keep their bucket, whether privacy projection applies inside the badge, the default-arm response shape, the enumeration bound, and which advertised groupBy enum values actually have arms — an advertised-but-unimplemented dimension silently degrades to the default arm (the workspace customers/count partnerId case), so either implement the arm or drop it from the schema. Adapt the inline-vs-builder placement of self-exclusion to your codebase's duplication tolerance. Omit zero-filling only if your UI tolerates empty breakdowns — otherwise adopt the payout-count-eligibility enum fill on top of this grammar.
