<!-- capsule-v2 -->
# Orphaned-anonymous-user reaper — how do you bulk-delete rows whose blast radius is schema-defined, unattended, without destroying someone's data?

**Source:** Rallly AGPL-3.0 `main@1b085700afec1dd5aa0eca419133dcba9bcdc9d6`; Codebase Memory `rallly`. **Question:** A recurring cron deletes anonymous guest accounts outright — what makes that safe when every `onDelete: Cascade` relation on User is inside the blast radius and the job runs unattended?

## Shared read/delete predicate + delete-time re-check + CI exhaustiveness buckets
**Path/Symbol:** `apps/web/src/features/user/mutations.ts:deleteOrphanedAnonymousUsers` (lines 155–245); CI guard `scripts/check-user-cascade-relations.mjs` (whole file, 284 lines); route `app/api/house-keeping/[...method]/route.ts` (lines 185–196, CRON_SECRET-guarded per housekeeping-cron-routes).
**Signature:** `deleteOrphanedAnonymousUsers() → number` (deleted count); cron route returns `{ success: true, summary: { deleted: { anonymousUsers } } }`.
**Data Shape:** one predicate object (`orphanedAnonymousFilter`, lines 196–213) used by BOTH the snapshot read and the delete; batch size 1000 (line 155, sized against the handler's maxDuration budget); liveness cutoff = `now - SESSION_TTL_SECONDS` (60 days, `lib/auth-config.ts:4`).

### Decisive source
```ts
// Both guards live here so read and delete share exactly one predicate.
const orphanedAnonymousFilter = {
  isAnonymous: true,
  lastSeenAt: { lt: cutoff },          // liveness: session TTL == window
  polls: { none: {} }, comments: { none: {} }, participants: { none: {} },
  scheduledEventInvites: { none: {} }, scheduledEvents: { none: {} },
  hostedEventTypes: { none: {} }, hostedSheets: { none: {} }, spaces: { none: {} },
  memberOf: { none: {} }, spaceMemberInvites: { none: {} }, subscriptions: { none: {} },
  paymentMethods: { none: {} }, calendarConnections: { none: {} }, credentials: { none: {} },
} satisfies Prisma.UserWhereInput;

while (hasMore) {
  const batch = await prisma.user.findMany({ where: orphanedAnonymousFilter, select: { id: true }, take: BATCH });
  if (batch.length === 0) break;
  // Re-apply the guards at delete time, not just id: a poll/comment/invite created
  // between this snapshot and the delete would otherwise be cascaded away.
  const { count } = await prisma.user.deleteMany({
    where: { AND: [orphanedAnonymousFilter, { id: { in: batch.map((u) => u.id) } }] },
  });
  deleted += count;
}
```

**Flow:** cron → cutoff from session TTL → loop: snapshot ids under the full filter → `deleteMany` with the FULL filter AND-ed onto the id list → ids that fail the re-check simply drop out and are excluded by the next snapshot → until an empty batch. The CI script parses every Prisma model for `onDelete: Cascade` relations on User, resolves each to its User-side field, and requires each to land in exactly one bucket: guarded (named in the purge filter) or ignored (`IGNORED_RELATIONS` map at line 38, each entry carrying a stated reason — sessions/accounts/notificationPreferences are auth plumbing every guest has, and filtering on them would make the purge match nothing). Unclassified relations and stale ignore entries both exit 1.
**Invariant:** two guards, both required, in ONE object so read and delete can never drift apart. The liveness guard works because prod sessions live in Redis (unprobeable) and the TTL equals the window: any session belonging to a guest below the cutoff has already expired by construction, and a returning guest's fresh session writes `lastSeenAt`, lifting them back above it. The delete-time re-check closes the snapshot→delete race: a poll created in between keeps the guest alive instead of being cascaded away. The CI script turns "the filter must stay exhaustive" from a comment into a failing build — the doc comment records that the app-code invariant (anonymous users get no space provisioned) is NOT a database constraint, so the filter does not rely on it holding.
**Probe:** no vitest suite for this function (caveat recorded); the executable guard is `scripts/check-user-cascade-relations.mjs` (direct read: model parser, guarded-set extraction bounded to the function body, unclassified/stale-ignored failure modes). Behavioral anchors verified by direct read: cutoff at mutations.ts:193, filter at :196–213, re-check deleteMany at :234–238, batch constant at :155; SESSION_TTL_SECONDS = 60 days at lib/auth-config.ts:4; route wiring at house-keeping route :185–186.

## Get live surrounding code
```ts
await mcp.codebase_memory.search_graph({ project: "rallly", query: "deleteOrphanedAnonymousUsers", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the shared-predicate + delete-time-recheck pattern for ANY bulk purge of rows with cascading children — it costs one extra WHERE clause and removes an entire race class. Adopt the two-bucket CI exhaustiveness check for any schema-defined blast radius: guarded vs ignored-with-reason, stale entries fail too. Adapt the liveness proxy to your session store (if you CAN probe sessions, probe them; the TTL-window trick exists because Redis can't be probed cheaply at delete time). Omit the batch loop only if your table is small enough that one deleteMany is safe under lock-budget. Caveat: no direct unit test; safety rests on the CI script plus the predicate shape.
