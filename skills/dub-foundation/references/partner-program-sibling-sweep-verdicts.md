<!-- capsule-v2 -->
# Partner program sibling sweep verdicts — which enrollment-scoped read routes are truly thin, and what invariants hide in the ones that look thin?

**Source:** dub AGPL-3.0-or-later `main@29df217a2963`; Codebase Memory `dub`. **Question:** When auditing the small routes around a partner program enrollment (submitted-leads, activity-logs, users), how do you decide thin-wrapper vs hidden-invariant — and what do the non-thin ones carry?

## Connected graph-selected seam
**Path/Symbol:** `apps/web/app/(ee)/api/partner-profile/programs/[programId]/submitted-leads/route.ts:GET` (:12-55) · `.../activity-logs/route.ts:GET` (:12-65) · `apps/web/app/(ee)/api/partner-profile/users/route.ts:GET/PATCH/DELETE` (:15-55 / :63-133 / :140-198) · workspace twin `apps/web/app/(ee)/api/programs/[programId]/submitted-leads/route.ts:GET` (:13-72).
**Signature:** all `withPartnerProfile(...)`; users PATCH `{requiredPermission: "users.update"}`; workspace twin `withWorkspace(..., { requiredPlan: ["business","advanced","enterprise"] })`.
**Data Shape:** submitted-leads: `{status?, search?, page=1, pageSize}` → strict `partnerProfileSubmittedLeadSchema[]`; activity-logs: `{resourceType, resourceId, action}` → `activityLogSchema[]` tail of 100; users: `{search?, role?}` → `partnerUserSchema[]`, PATCH `{userId, role}`, DELETE `?userId=`.

### Decisive source
```ts
// activity-logs — NOT thin: hard resource-type gate + TRIPLE-SCOPED existence oracle before any log read:
// Limit to submitted lead for now
if (resourceType !== "submittedLead") { throw new DubApiError({ code: "bad_request", ... }); }  // :17-23
const lead = await prisma.submittedLead.findUnique({
  where: { id: resourceId, programId: programEnrollment.programId, partnerId: partner.id },  // :32-37 triple scope
  select: { id: true },
});
if (!lead) throw new DubApiError({ code: "not_found", message: "Submitted lead not found." });  // :43-48
const activityLogs = await prisma.activityLog.findMany({ where: {...}, orderBy: { createdAt: "desc" }, take: 100 });  // :50-61 bounded tail
```
```ts
// users GET — merge order is load-bearing: user fields override join fields EXCEPT createdAt:
const parsedUsers = users.map(({ user, ...rest }) =>
  partnerUserSchema.parse({ ...rest, ...user, createdAt: rest.createdAt }),  // :46-52 preserve the PartnerUser join timestamp
);
// users PATCH — self-role-change forbidden, then find+count(owner)+update in ONE $transaction (TOCTOU):
if (userId === session.user.id) throw new DubApiError({ code: "forbidden", message: "You cannot change your own role." });  // :69-74
const [partnerUserFound, totalOwners] = await Promise.all([tx.partnerUser.findUnique({...}), tx.partnerUser.count({ where: { partnerId, role: "owner" } })]);  // :78-94
if (totalOwners === 1 && partnerUserFound.role === "owner" && role !== "owner") {
  throw new DubApiError({ code: "bad_request", message: "Cannot change the role of the last owner..." });  // :103-113 LAST-OWNER GUARD
}
// users DELETE — SELF-REMOVAL bypasses the permission check but NOT the guard:
const isSelfRemoval = userToRemove.userId === partnerUser.userId;   // :172
if (!isSelfRemoval) throwIfNoPermission({ role: partnerUser.role, permission: "users.delete" });  // :174-179
if (totalOwners === 1 && userToRemove.role === "owner") throw new DubApiError({ code: "bad_request", ... });  // :181-187 same guard, inside the same $transaction
```
**Flow:** Verdict 1 — submitted-leads partner twin IS thin: enrollment gate → scoped `findMany` (programId + partnerId) → strict parse; it carries one @-search-ladder instance (`search.includes("@")` ⇒ exact email else full-text email+name via `sanitizeFullTextSearch`, :35-42). Its WORKSPACE twin is thin-plus: default status exclusion when no status given (`notIn: [unqualified, closedLost]`, :29-38), partner include (:48-57), business+ plan gate (:70). Thinness is per-auth-context, not per-resource. Verdict 2 — activity-logs is NOT thin: single-resourceType hard gate, then the resource id must match programId AND partnerId AND id before the log table is touched, and the result is a bounded tail (`take: 100`). Verdict 3 — users REFUTES thinness entirely: the three handlers above.
**Invariant:** (1) The existence oracle scopes the probed resource to (programId, partnerId) BEFORE reading logs — a partner cannot probe another partner's lead activity by guessing ids. (2) The last-owner guard reads the owner count INSIDE the same `$transaction` as the mutation (TOCTOU-safe): demoting or removing the sole owner is rejected, so a profile can never be orphaned. (3) Self-removal needs no `users.delete` permission but still hits the guard — members can leave, nobody can strand the profile. (4) The GET merge order `{...rest, ...user, createdAt: rest.createdAt}` keeps the MEMBERSHIP timestamp, not the user row's createdAt — a silent re-order would corrupt join-age reporting.
**Probe:** No direct tests (`tests/**/*partner-user*|*activity-log*|*submitted-lead*` = ∅). Deterministic probes executed at pin: "Limit to submitted lead" comment :17; `$transaction` count = 2 in users/route.ts (PATCH + DELETE); "preserve the createdAt" :50; `unqualified`/`closedLost` at workspace twin :34-35; "You cannot change your own role." :72; `take: 100` :60.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dub", qn_pattern: ".*/partner-profile/.*", name_pattern: "^(GET|PATCH|DELETE)$", limit: 20 }); // sibling route census
await mcp.codebase_memory.search_graph({ project: "dub", query: "last owner guard partner user role transaction", limit: 10 }); // rank-1 expected: users PATCH/DELETE guards
```

## Verdict
Adopt the sweep method itself: classify each small route as thin only after checking for (a) hard input gates, (b) scoped existence oracles, (c) transactional mutation guards, (d) load-bearing serialization order. Adopt the triple-scoped oracle, the in-transaction last-owner guard, and the self-removal permission bypass with guard retention. Adapt the single-resourceType whitelist to your audit-log model and the 100-row tail to your UI. Omit nothing from the guard set — each was added to close a specific race or probe, not for style.
