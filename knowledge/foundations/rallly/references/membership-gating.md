<!-- capsule-v2 -->
# Membership gating — when is space membership "effective" and what do guests get to keep?

**Source:** Rallly AGPL-3.0 `main@1b085700afec1dd5aa0eca419133dcba9bcdc9d6`; Codebase Memory `rallly`. **Question:** How does a downgraded (hobby) space restrict access, and which poll capabilities stay open to guest participants?

## effectiveSpaceMemberWhere + poll open-capability rules
**Path/Symbol:** `apps/web/src/features/space/member/utils.ts:effectiveSpaceMemberWhere` (11–20); consumed by `hasPollAdminAccess`/`canUserManagePoll` in `apps/web/src/features/poll/data.ts` (352–406); client capability gate `apps/web/src/features/poll/client.tsx:usePermissions` (43–81).
**Signature:** `effectiveSpaceMemberWhere({ userId }) → { userId } | { userId, OR: [space.tier=pro, space.ownerId=userId] }`.
**Data Shape:** billing-enabled builds restrict membership effect; disabled/self-hosted treat every member as effective.

### Decisive source
```ts
// Membership in a hobby space is only effective for the space owner, so a
// downgraded space locks out its other members until it is upgraded again.
// Apply to every user-scoped membership resolution query. Only enforced
// when billing is enabled: without an upgrade path there is nothing to
// gate, and self-hosted spaces are treated as pro regardless of the tier
// stored in the database.
```
```ts
canAddNewParticipant: poll.status === "open",
canEditParticipant: (participantId) => {
  if (poll.status !== "open") return false;
  /* admin ⇒ any; else own row only, incl. impersonated user */
},
```

**Flow:** every membership query (poll admin checks, space reads) funnels through this one predicate → downgrade becomes instant lockout for non-owners without touching rows. Separately, the CLIENT gates voting capability purely on poll.status === "open" — guests never need accounts to vote while open; the server enforces the same via possiblyPublicProcedure + requireUserMiddleware on add.
**Invariant:** one predicate, applied EVERYWHERE membership resolves — sprinkling tier checks at call sites guarantees drift; the closed/auto-closed ladder (see poll-lifecycle capsule) flips status, and THIS predicate is what makes closing actually freeze edits on both sides.
**Probe:** deterministic grep anchors: `grep -c 'poll.status === "open"' apps/web/src/features/poll/client.tsx` → 1 (line 52, canAddNewParticipant; the edit gate at :54 is the negated `poll.status !== "open"`); `grep -cF 'isBillingEnabled' apps/web/src/features/space/member/utils.ts` → 2.

## Get live surrounding code
```ts
await mcp.codebase_memory.search_graph({ project: "rallly", query: "effectiveSpaceMemberWhere spaceMember", limit: 5 });
```

## Verdict
Adopt the single-predicate rule + status-frozen-editing coupling verbatim; adapt tier enum/billing flag; omit impersonation context if absent. Source-pinned; no direct test file.
