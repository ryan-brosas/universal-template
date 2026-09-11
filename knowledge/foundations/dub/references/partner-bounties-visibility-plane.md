<!-- capsule-v2 -->
# Partner bounties visibility plane — how do you show a partner only the bounties they can act on, while keeping their past submissions visible?

**Source:** dub AGPL-3.0-or-later `main@29df217a2963`; Codebase Memory `dub`. **Question:** A bounty can be expired, audience-restricted, or archived — yet a partner who already submitted must still see it. What kernel separates "can see" from "can submit", and how is eligibility enforced at both SQL and JS level?

## Connected graph-selected seam
**Path/Symbol:** `apps/web/app/(ee)/api/partner-profile/programs/[programId]/bounties/route.ts:GET` (:7-38) · `.../bounties/[bountyId]/route.ts:GET` (:15-106) · `apps/web/lib/bounty/api/bounty-availability.ts` (buildBountyEligibilityWhere :42-99, buildBountyActivePeriodWhere :103-128, getEffectiveBountyPeriod :144-163, isPartnerEligibleForBounty :165-235, canPartnerSeeBounty :237-259, canPartnerSubmitBounty :262-277) · `apps/web/lib/bounty/api/get-bounties-for-partner.ts:getBountiesForPartner` (:30-123) · `apps/web/lib/bounty/api/get-bounty-or-throw.ts:getBountyOrThrow` (:14-38).
**Signature:** both routes under `withPartnerProfile`; enrollment fetched with program(defaultGroupId) + links(stats cols) + programPartnerTags includes; list returns `z.array(PartnerBountySchema).parse(...)`; detail returns one parsed object with computed startsAt/endsAt/performanceCondition/partner stats.
**Data Shape:** bounty rows carry startMode (absolute|relative), startsAt/endsAt/endsAfterDays, groups[]/partnerTags[] audience relations, submissions[] pre-filtered to THIS partner; enrollment carries groupId/status/createdAt/totalCommissions.

### Decisive source
```ts
// visibility ≠ submittability (bounty-availability.ts :237-277)
export const canPartnerSeeBounty = ({ program, bounty, programEnrollment }) => {
  if (bounty.archivedAt) return false;
  // Bounties the partner has a submission on stay visible
  if (bounty.submissions.length > 0) return true;      // :251 — past work survives expiry/ineligibility
  return isPartnerEligibleForBounty({ program, bounty, programEnrollment });
};
export const canPartnerSubmitBounty = ({ program, bounty, programEnrollment }) => {
  if (!ACTIVE_ENROLLMENT_STATUSES.includes(programEnrollment.status)) return false;  // [approved, archived] (partners.ts :38-41)
  return isPartnerEligibleForBounty({ program, bounty, programEnrollment });
};
```
```ts
// audience grammar (buildBountyEligibilityWhere :42-99): empty = open to all; else group AND tag
AND: [
  { OR: [ { groups: { none: {} } }, ...(groupIds.length ? [{ groups: { some: { groupId: { in: groupIds } } } }] : []) ] },
  { OR: [ { partnerTags: { none: {} } }, ...(partnerTagIds.length ? [{ partnerTags: { some: { partnerTagId: { in: partnerTagIds } } } }] : []) ] },
]
// group resolution: enrollment.groupId || program.defaultGroupId (get-bounties-for-partner.ts :35)
```
```ts
// relative vs absolute periods (getEffectiveBountyPeriod :144-163 + isPartnerEligibleForBounty :208-209)
const bountyStartDate = startMode === BountyStartMode.absolute ? startsAt! : createdAt;   // relative ⇒ PER-PARTNER start = enrollment.createdAt
return { startsAt: bountyStartDate, endsAt: endsAfterDays ? addDays(bountyStartDate, endsAfterDays) : endsAt };
if (bounty.startMode === BountyStartMode.relative && programEnrollment.createdAt < bounty.createdAt) return false;  // relative bounties are NEW-PARTNER-ONLY
```
```ts
// DOUBLE ENFORCEMENT (get-bounties-for-partner.ts :42-57 then :88-92)
where: { programId, archivedAt: null, OR: [
  { submissions: { some: { partnerId } } },                       // arm 1: has my submission
  { AND: [ buildBountyEligibilityWhere({groupId, partnerTagIds}), buildBountyActivePeriodWhere() ] },  // arm 2: eligible ∧ active now
]},
...
const visibleBounties = bounties.filter((bounty) => canPartnerSeeBounty({...}));  // JS re-check of the same predicate
```
**Flow:** route fetches enrollment (incl. link stats + tags) → list: single findMany with OR[has-submission, eligibility∧active-period], then JS re-filter, then per-bounty period computation + PartnerBountySchema.parse; detail: getBountyOrThrow (missing AND cross-program both → not_found "Bounty <id> not found.") → canPartnerSeeBounty gate → not_found when false (:80-84) → compute effective period, fold workflow.triggerConditions[0] as performanceCondition, fold aggregatePartnerLinksStats + totalCommissions into partner slot.
**Invariant:** (1) Visibility and submittability are SEPARATE predicates over ONE shared eligibility core: seeing keeps any bounty with an existing submission visible forever (archived still hides it); submitting additionally requires an active enrollment status. (2) Eligibility is enforced TWICE — SQL pre-filter (cheap, wrong rows never fetched) and JS re-check (source of truth, also used by the detail route which has no list query); the two must stay semantically identical or the detail route leaks. (3) Relative bounties anchor their window to EACH partner's enrollment createdAt (per-partner endsAfterDays), and exclude partners who enrolled before the bounty existed. (4) Existence oracles are suppressed twice: cross-program bounties report the same not_found as missing ones, and ineligible bounties report not_found rather than forbidden.
**Probe:** No direct test for the partner-profile bounties routes (tests/bounties/ contains only upsert-draft-bounty-submissions.test.ts, which pins the draft-upsert kernel, not this read surface). Deterministic probes executed at pin: `submissions.length > 0` at bounty-availability.ts:251; `ACTIVE_ENROLLMENT_STATUSES.includes` at :268 with the constant = [approved, archived] at lib/zod/schemas/partners.ts:38-41; `none: {}` ×2 + `some: {` ×2 inside buildBountyEligibilityWhere (:59/:66/:81/:88); `programEnrollment.createdAt < bounty.createdAt` at :209; detail-route not_found at [bountyId]/route.ts:82.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dub", query: "canPartnerSeeBounty canPartnerSubmitBounty isPartnerEligibleForBounty", limit: 5 }); // availability kernel
await mcp.codebase_memory.search_graph({ project: "dub", file_pattern: "*partner-profile*bounties*", name_pattern: "^GET$", limit: 10 }); // the three routes
```

## Verdict
Adopt the two-predicate split (see vs submit) over one shared eligibility core, the empty-means-open audience grammar (group AND tag, none:{} arms), per-partner relative windows anchored on enrollment createdAt, and double enforcement (SQL pre-filter + JS re-check kept identical). Adopt oracle suppression: not_found for missing, cross-scope, AND ineligible. Adapt the audience dimensions to your tenancy model; omit the JS re-check only if you have exactly one read path. Caveat: no direct test exists for this surface; anchors are line-pinned at the pin.
