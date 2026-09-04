<!-- capsule-v2 -->
# Partner earnings list kernel — how does one auth-free kernel serve both embed and partner-profile callers with different privacy flags?

**Source:** dub AGPL-3.0-or-later `main@29df217a2963`; Codebase Memory `dub`. **Question:** Where should privacy projection live when two callers of the same earnings query have DIFFERENT data-sharing policies?

## Connected graph-selected seam
**Path/Symbol:** `apps/web/lib/api/partner-profile/get-earnings-for-partner.ts:getEarningsForPartner` (:19-139); caller `.../programs/[programId]/earnings/route.ts:GET` (:8-28).
**Signature:** `getEarningsForPartner(params: z.infer<getPartnerEarningsQuerySchema> & { programId, partnerId, customerDataSharingEnabledAt: Date | null })`.
**Data Shape:** In: paging/sort + filters (type,status,linkId,customerId,payoutId) + window (interval|start/end + timezone). Out: `z.array(PartnerEarningsSchema)` rows where `customer` may be a substituted source PARTNER.

### Decisive source
```ts
const earnings = await prisma.commission.findMany({
  where: { earnings: { not: 0 }, programId, partnerId, status, type,
           linkId, customerId, payoutId,
           createdAt: { gte: startDate, lte: endDate } },          // :50-52 — zero-earning rows never listed
  include: { customer: {...}, link: {...} },
});
// TODO: Once we migrate to add sourcePartner relation on Commission table...   // :89
let sourcePartners = await prisma.partner.findMany({ where: { id: { in: referralSourceIds } } }); // :95-107 batched
if (e.type === CommissionType.referral && e.sourcePartnerId) {
  const sourcePartner = sourcePartners.find((p) => p.id === e.sourcePartnerId);
  if (sourcePartner) e.customer = sourcePartner;                  // :112-118 — referral rows show the SOURCE PARTNER in the customer slot
}
const customerEmail = e.customer?.email || e.customer?.name || generateRandomName(); // :122-123 fallback ladder
email: customerDataSharingEnabledAt ? customerEmail : obfuscateCustomerEmail(customerEmail),       // :130-132 flag-gated
return z.array(PartnerEarningsSchema).parse(...);                 // :110 exit gate
```

**Flow:** resolve window via getStartEndDates → windowed commission.findMany (`earnings != 0`) with customer+link includes → batched source-partner fetch for referral rows → per-row substitution (referral ⇒ source partner occupies the customer slot) → email fallback chain email→name→random name THEN flag-gated obfuscation → strict schema parse.
**Invariant:** The kernel is AUTH-FREE and takes `customerDataSharingEnabledAt` as an explicit parameter — each route passes ITS OWN enrollment's flag (embed/referrals/earnings and programs/[programId]/earnings are the two inbound callers, trace callers_total=2), so one query implementation serves two privacy postures without branching inside the kernel. Referral-row partner substitution is a documented stopgap (in-code TODO) until a real relation exists.
**Probe:** No direct test (embed-tokens/referrals.test.ts pins token minting, not earnings reads — verified this run). Deterministic probes: `not: 0` :51, TODO comment :89, referral predicate :92/:112, fallback ladder :123, obfuscate branch :130-132.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dub", query: "getEarningsForPartner partner earnings", limit: 5 });
await mcp.codebase_memory.trace_path({ project: "dub", function_name: "getEarningsForPartner", direction: "inbound", depth: 1 }); // callers_total=2
```

## Verdict
Adopt the parameter-threaded privacy flag on an auth-free kernel so multiple hosts share one projection implementation. Adapt the source-partner substitution to a real relation if you control the schema (dub's TODO says it would). Omit the random-name filler if your product prefers null customers.
