<!-- capsule-v2 -->
# Participant visibility ladder — what does hideParticipants actually hide, per viewer?

**Source:** Rallly AGPL-3.0 `main@1b085700afec1dd5aa0eca419133dcba9bcdc9d6`; Codebase Memory `rallly`. **Question:** For each (viewer, poll.hideParticipants, participant.userId) combination, which fields are stripped server-side?

## participants.list DTO stripping + note privacy
**Path/Symbol:** `apps/web/src/trpc/routers/polls/participants.ts:list` (lines 120–212), DTO builder `createParticipantFullDTO` (lines 32–44).
**Signature:** `list({ pollId, token? }) → Array<ParticipantDTO & { hidden: boolean; note: string | null }>`; note stripped to null for non-author non-admin viewers.
**Data Shape:** stripped shape zeroes identity: `{ userId: null, name: "", email: null, image: null, hidden: true }`.

### Decisive source
```ts
// Response notes are visible to the host and their author only: strip
// them from every other payload rather than hiding them in the UI.
const participants = rawParticipants.map((participant) => {
  const dto = createParticipantFullDTO(participant);
  if (isAdmin || (participant.userId && participant.userId === viewerId)) {
    return dto;
  }
  return { ...dto, note: null };
});

// Hide participants if the poll has hideParticipants enabled
// and the current user is not an admin
if (poll.hideParticipants) {
  if (!isAdmin) {
    return participants.map((participant) => {
      if (viewerId && participant.userId === viewerId) return participant;
      return { ...participant, userId: null, name: "", email: null, image: null, hidden: true };
    });
  }
}
```

**Flow:** deleted-poll 404 → fetch live participants (createdAt desc, name desc tiebreak) → compute isAdmin (session only) and viewerId (token fallback) → strip notes from non-privileged payloads → if hiding enabled and not admin, anonymize everyone except the viewer's own row. The client renders votes/avatars from whatever arrives; there is no client-side hiding to bypass.
**Invariant:** redaction is SERVER-SIDE payload shaping, not UI filtering — a porter moving this into components leaks identities via the network response. Votes stay public even when identities are hidden (the poll's purpose); ordering is deterministic (createdAt desc then name desc) so redaction can't be defeated by array-position correlation.
**Probe:** deterministic grep anchors: `grep -n 'name: ""' apps/web/src/trpc/routers/polls/participants.ts` → exactly 1 hit (line 202); `grep -n "note: null" apps/web/src/trpc/routers/polls/participants.ts` → exactly 1 hit (line 187).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "rallly", query: "participants list hideParticipants hidden", limit: 5 });
```

## Verdict
Adopt the two-stage strip (note privacy always-on; identity hiding under flag) verbatim; adapt the DTO shape; omit the deprecated `hideParticipants` input param. No dedicated test file — boundary is comment-pinned in source.
