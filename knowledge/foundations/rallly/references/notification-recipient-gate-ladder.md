<!-- capsule-v2 -->
# Notification recipient gate ladder — in what order must "should the poll creator be emailed?" gates run, and who is silently skipped?

**Source:** Rallly AGPL-3.0 `main@1b085700afec1dd5aa0eca419133dcba9bcdc9d6`; Codebase Memory `rallly`. **Question:** Which conditions suppress a creator notification, where do they live relative to the DB queries, and why does the per-type preference check come last?

## getNotificationRecipient ordered null-ladder
**Path/Symbol:** `apps/web/src/features/notifications/data.ts:getNotificationRecipient` (lines 39–89); consumed by `apps/web/src/trpc/routers/polls/participants.ts:sendNewResponseNotificationEmail` (lines 71–117) and `apps/web/src/trpc/routers/polls/comments.ts:add` (lines 149–177).
**Signature:** `getNotificationRecipient({ pollId, type, excludeUserId }) → Promise<{ id; email; locale } | null>` — null means "send nothing", never an error.
**Data Shape:** poll probe selects exactly `{userId, muted, deleted}`; creator probe filters `isAnonymous: false` IN the where clause and pulls prefs via the relation.

### Decisive source
```ts
const poll = await prisma.poll.findUnique({
  where: { id: pollId },
  select: { userId: true, muted: true, deleted: true },
});

if (!poll?.userId || poll.deleted || poll.userId === excludeUserId || poll.muted) {
  return null;
}

const creator = await prisma.user.findUnique({
  where: { id: poll.userId, isAnonymous: false },
  select: { id: true, email: true, locale: true, notificationPreferences: { select: { prefs: true } } },
});

if (!creator) {
  return null;
}

const prefs = parsePrefs(creator.notificationPreferences?.prefs);

if (!prefs[type]) {
  return null;
}

return { id: creator.id, email: creator.email, locale: creator.locale };
```

**Flow:** cheap single-poll probe first (missing row / soft-deleted poll / actor IS the creator / per-poll mute all return before any user query) → creator fetch with anonymity filtered in SQL (a guest-created poll whose "creator" is an anonymous user row yields null) → only then decode prefs (see `activity-event-prefs-codec`) and check THIS event type → return the recipient triple.
**Invariant:** the gate order is a cost-and-correctness contract: everything knowable from one poll row short-circuits before the user fetch, and the per-type pref check must come AFTER the user fetch because prefs live on the user's relation. The actor self-exclusion lives HERE, not at call sites — every new notification type gets it for free by routing through this function. Callers treat null as a silent no-op wrapped in their own try/catch (see `deferred-email-dispatch` for the transport half).
**Probe:** deterministic grep anchors (executed): `grep -n 'isAnonymous: false' apps/web/src/features/notifications/data.ts` → line 63; `grep -c 'return null' apps/web/src/features/notifications/data.ts` → 3 (the first gate collapses missing-row/deleted/self/muted into ONE exit at :59; then :75 no-creator and :81 pref-off). No dedicated upstream test for the ladder.

## Get live surrounding code
```ts
await mcp.codebase_memory.search_graph({ project: "rallly", query: "getNotificationRecipient excludeUserId muted", limit: 5 });
```

## Verdict
Adopt the ladder order and the central-gate placement verbatim (new event types plug in via `type`, gates stay shared); adapt the anonymity filter to your user model; omit nothing. Cross-ref: `deferred-email-dispatch` owns after()/catch-log transport; this capsule owns only WHO qualifies.
