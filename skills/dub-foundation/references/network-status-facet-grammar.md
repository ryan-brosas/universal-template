<!-- capsule-v2 -->
# Network status facet grammar — how do you keep list, count-facet, and metering views of one lifecycle consistent across three query dialects?

**Source:** dub AGPL-3.0-or-later `main@29df217a29631ced4041882a28d2327cc4546f27`; Codebase Memory `dub`. **Question:** when the same partner lifecycle (discover/invited/recruited/ignored) is served by a Prisma list route, a count-facet route, and a billing meter, how does dub keep the three dialects from drifting?

## Network status facet grammar
**Path/Symbol:** `apps/web/lib/api/network/partner-network-listing-where.ts:partnerNetworkListingParts` (:29-39) + `partnerWhereFromListingParts` (:47-56); `apps/web/app/(ee)/api/network/partners/count/route.ts:GET` statusWheres (:45-93) + groupBy arms (:100-155); `apps/web/lib/api/partners/get-network-invites-usage.ts:getNetworkInvitesUsage` (:5-25).
**Signature:** `partnerNetworkListingParts({ partnerIds?, country?, platform? }): PartnerNetworkListingParts`; `getNetworkInvitesUsage(workspace: Pick<Project, "id" | "billingCycleStart">): Promise<number>`.
**Data Shape:** parts split the shared slice into `listingPartnerBase` (networkStatus IN approved/trusted + id/country) and `listingPlatformSome` (verifiedAt not-null + type) so the count route can reuse the base WITHOUT the platforms relation nesting; statusWheres is a const record keyed by the four lifecycle states.

### Decisive source
```ts
// count/route.ts :49-58 — the discover arm admits "no record yet" as discoverable
OR:
  starred === true
    ? [
        {
          discoveredByPrograms: {
            some: { programId, starredAt: { not: null } },
          },
        },
      ]
    : starred === false
      ? [
          { discoveredByPrograms: { none: { programId } } }, // No record yet
          {
            discoveredByPrograms: {
              some: { programId, starredAt: null, ignoredAt: null },
            },
          }, // Not starred and not ignored
        ]
      : [
          { discoveredByPrograms: { none: { programId } } }, // No record yet
          {
            discoveredByPrograms: {
              some: { programId, ignoredAt: null },
            },
          }, // Has record but not ignored
        ],
```

**Flow:** list route (partners/route.ts :58-113): status !== "discover" ⇒ Prisma findMany on DiscoveredPartner with per-status where+orderBy (ignored ⇒ ignoredAt not-null + ignoredAt desc; invited ⇒ invitedAt not-null + ignoredAt null + enrollment status "invited" + invitedAt desc; recruited ⇒ invitedAt not-null + enrollment status "approved" + enrollment createdAt desc) and NetworkPartnerSchema.parse exit. Count route: groupBy=status ⇒ four parallel partner.count calls (each facet SKIPPED — undefined — when a specific status was requested, so only the requested facet hits the DB); groupBy=country ⇒ partner.groupBy by country _count desc; any other groupBy (platform/subscribers are ADVERTISED in the schema enum) throws raw Error("Invalid groupBy") :157. Metering: getNetworkInvitesUsage counts DiscoveredPartner rows where invitedAt OR messagedAt > getBillingStartDate(billingCycleStart) — two distinct engagement timestamps share one billing-window budget; the invites-usage route projects usage/limit/remaining with Math.max(0, ·) floor, and the kernel is re-consumed by invite-partner-from-network (:29) and message-partner (:115) which enforce the limit themselves.
**Invariant:** "discoverable" always means networkStatus IN (approved, trusted) + verified platform + not-enrolled, and the ABSENCE of a DiscoveredPartner row is a valid discover state (none: {programId} OR ignoredAt null) — the count facet and the ranking kernel's `enrolled.id IS NULL`/`dp.ignoredAt IS NULL OR dp.id IS NULL` conditions must stay semantically identical across dialects; the meter counts invitations, not enrollments, so a rejected invite still consumes budget.
**Probe:** no direct test (grep tests/ = ∅); deterministic probes: groupBy==="status" :100, groupBy==="country" :142, `Invalid groupBy` :157, discoveredByPrograms ×8, starred===true :49, networkStatus IN :35 (listing-where), verifiedAt not-null :22, invitedAt :16 + messagedAt :21 (usage), Math.max(0 :13 (route), getNetworkInvitesUsage callers = invites-usage route + invite-partner-from-network :29 + message-partner :115; negative: zero groupBy==="platform"/"subscribers" arms in the count route (advertised-enum-vs-implemented-arms quirk, sixth-axis sibling of count-badge-groupby-grammar).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dub", query: "partnerNetworkListingParts statusWheres discoveredByPrograms facet count", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the parts-split (base vs relation-scoped slice) for sharing a where-grammar between a list and a count route, the skip-undefined facet pattern (only requested facets query), and the two-timestamp billing meter. Adapt the four-state lifecycle names, Prisma relation shapes, and the billing-cycle anchor. Omit the raw Error("Invalid groupBy") fallback — replace with a typed 422; treat the advertised-but-unimplemented enum arms as a trap to check in your own port. Coverage caveat: no direct test exists; evidence is whole-file source reads + executed grep probes at the pin.
