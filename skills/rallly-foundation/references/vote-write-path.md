<!-- capsule-v2 -->
# Vote write path — how are vote updates made safe against stale option ids and activity detection?

**Source:** Rallly AGPL-3.0 `main@1b085700afec1dd5aa0eca419133dcba9bcdc9d6`; Codebase Memory `rallly`. **Question:** What is the exact transactional shape of "change my votes", and which client-side normalization must precede it?

## participants.update delete-all/create-valid + normalizeVotes
**Path/Symbol:** `apps/web/src/trpc/routers/polls/participants.ts:update` (lines 437–529); client `apps/web/src/features/poll/components/mutations.ts:normalizeVotes` (lines 8–16).
**Signature:** `update({ pollId, participantId, votes: {optionId; type}[], token? }) → ParticipantDTO`; server filters votes to existing option ids inside the tx.
**Data Shape:** full-row replace (deleteMany + createMany), not per-vote diffing.

### Decisive source
```ts
const participant = await prisma.$transaction(async (tx) => {
  // Delete existing votes
  await tx.vote.deleteMany({ where: { participantId } });
  const options = await tx.option.findMany({ where: { pollId }, select: { id: true } });
  const existingOptionIds = new Set(options.map((option) => option.id));
  const validVotes = votes.filter(({ optionId }) => existingOptionIds.has(optionId));
  // Create new votes
  await tx.vote.createMany({ data: validVotes.map(({ optionId, type }) => ({ optionId, type, pollId, participantId })) });
  // Bump `updatedAt` ... An empty `data: {}` update is a no-op for `@updatedAt`
  return tx.participant.update({ where: { id: participantId }, data: { updatedAt: new Date() }, /* include votes,user */ });
});
```
```ts
export const normalizeVotes = (optionIds, votes) =>
  optionIds.map((optionId, i) => ({ optionId, type: votes[i]?.type ?? ("no" as const) }));
```

**Flow:** resolveActor → canModifyParticipant (owner or poll admin) → ONE transaction: wipe all the participant's votes → filter incoming to currently-existing option ids (poll may have been edited mid-session) → insert fresh rows → explicit updatedAt bump. Client normalizes its sparse form array into a dense per-option list defaulting missing entries to "no" so the payload always covers every current option.
**Invariant:** replace-not-diff sidesteps upsert races and orphaned types entirely; stale optionIds are silently dropped rather than rejected (a poll edit between render and submit is a non-event); the updatedAt bump is what keeps the retention ladder from deleting an actively voting participant's poll.
**Probe:** deterministic grep anchors: `grep -cF 'existingOptionIds' apps/web/src/trpc/routers/polls/participants.ts` → 4 (set+filter in BOTH add and update); `grep -n 'votes[i]?.type ??' apps/web/src/features/poll/components/mutations.ts` → line 14.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "rallly", query: "participants update validVotes createMany", limit: 5 });
```

## Verdict
Adopt replace-in-transaction + stale-id filtering + explicit bump verbatim; adapt to your ORM's batch ops; omit the optimistic cache patching in the client hooks. No dedicated test file — shape pinned by source comments and cross-capsule coupling.
