<!-- capsule-v2 -->
# Soft-delete invisibility ladder — what does "deleted" mean for polls, participants, and votes?

**Source:** Rallly AGPL-3.0 `main@1b085700afec1dd5aa0eca419133dcba9bcdc9d6`; Codebase Memory `rallly`. **Question:** Which soft-deleted rows are filtered where, and why is a deleted poll invisible even to its owner?

## Deleted-poll 404 + participant/vote filtering
**Path/Symbol:** `apps/web/src/trpc/routers/polls.ts:get` (lines 674–681) + `hasPollAdminAccess` in `apps/web/src/features/poll/data.ts` (lines 390–406); participants filter `apps/web/src/trpc/routers/polls/participants.ts:list` (lines 141–145); vote aggregation `apps/web/src/features/poll/data.ts:getPollResults` (lines 45–52).
**Signature:** `get` throws `TRPCError NOT_FOUND` when `!res || res.deleted`; `hasPollAdminAccess(pollId, userId): Promise<boolean>` via findFirst with `deleted: false`.
**Data Shape:** poll.deleted + poll.deletedAt; participant.deleted; every aggregate joins through the live rows only.

### Decisive source
```ts
// A deleted poll is treated as if it never existed, for everyone
// including its owner and space managers.
if (!res || res.deleted) {
  throw new TRPCError({ code: "NOT_FOUND", message: "Poll not found" });
}
```
```ts
const [poll, voteCounts] = await Promise.all([
  prisma.poll.findFirst({ where: { id: pollId, spaceId, deleted: false }, /* ... */ }),
  prisma.vote.groupBy({
    by: ["optionId", "type"],
    where: { pollId, participant: { deleted: false } },   // ← votes of deleted participants excluded
    _count: true,
  }),
]);
```

**Flow:** markAsDeleted sets `deleted:true, deletedAt:new Date()` → every read path treats it as nonexistent: poll get → NOT_FOUND for ALL viewers; admin check (`hasPollAdminAccess`, `canUserManagePoll`) returns false on deleted; participants.list 404s before listing; scores exclude deleted participants' votes. Hard delete follows only after the 7-day purge window.
**Invariant:** deletion must be checked BEFORE any data leaves the API — a porter who filters only lists but still serves `polls.get` leaks the entire poll by URL. Note the two flag spellings coexist intentionally: newer code uses `deletedAt: null`, older reads use `deleted: false`; both must be respected per table.
**Probe:** `apps/web/src/features/poll/mutations.test.ts` ("scopes the lookup to the space and excludes deleted polls", :194) + `data.test.ts` ("scopes the query to the space and excludes deleted polls", :69).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "rallly", query: "hasPollAdminAccess canUserManagePoll deleted", limit: 5 });
```

## Verdict
Adopt the "deleted ⇒ 404 for everyone incl. owner" rule and the participant-scoped vote aggregation verbatim; adapt the flag spelling to one convention per table in your port (but keep both predicates during migration); omit nothing.
