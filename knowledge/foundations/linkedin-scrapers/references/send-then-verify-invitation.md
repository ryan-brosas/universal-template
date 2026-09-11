<!-- capsule-v2 -->
# Send-then-verify invitation — POST the invite, then read back the newest sent invitation as the return value (how do I get a usable handle on a write whose response carries no object)?

**Source:** linkedin-private-api MIT `master@e083f37`; Codebase Memory `linkedin-private-api`. **Question:** The norm-invitations POST returns no entity — how does the repo give callers a full `Invitation` (with profile joined) anyway, and what is the wire shape?

## Read-back pattern
**Path/Symbol:** `src/repositories/invitation.repository.ts:sendInvitation` (:59–73); request `src/requests/invitation.request.ts:sendInvitation` (:12–25); parser `parseInvitationResponse` (:14–34).
**Signature:** `sendInvitation({profileId, trackingId, message?}): Promise<Invitation>` — POST `growth/normInvitations`, then `this.fetchSent({skip: 0, limit: 1})[0]`.
**Data Shape:** payload `{trackingId, emberEntityName: 'growth/invitation/norm-invitation', invitee: {'com.linkedin.voyager.growth.invitation.InviteeProfile': {profileId}}, message?}`; sent-list GET `relationships/sentInvitationViewsV2?start&count&invitationType=CONNECTION&q=invitationType`; received twin `relationships/invitationViews?q=receivedInvitation`.

### Decisive source
```ts
async sendInvitation({ profileId, trackingId, message }): Promise<Invitation> {
  await this.client.request.invitation.sendInvitation({ profileId, trackingId, message });
  const lastInvitation = (await this.fetchSent({ skip: 0, limit: 1 }))[0];
  return lastInvitation;
}
const parseInvitationResponse = (idField) => (response) => {
  const profiles = keyBy(getProfilesFromResponse(response), 'entityUrn');   // keyed by URN here!
  const invitations = results.filter(r => r.$type === INVITATION_TYPE && !!r[idField]);
  return orderBy(invitations.map(inv => ({ ...inv, profile: profiles[inv[idField]] })), 'sentTime', 'desc');
};
```

**Flow:** fire the mutation (response ignored) → immediately GET the sent list limited to 1 → parse via the shared factory with direction-dependent join field (`'*toMember'` for sent, `'*fromMember'` for received) → newest-by-`sentTime` row IS the created invitation. The parser keys profiles by RAW entityUrn (not stripped id) because `*toMember/*fromMember` hold full miniProfile URNs — a deliberate key-choice difference from the profileId-keyed default.
**Invariant:** correctness rests on "the just-created invitation is the newest sent one" — true for single-account sequential sends, racy under concurrent invites (recorded; serialize sends or match by mailboxItemId in ports). `trackingId` comes from the CALLER (search hits carry it) and is required to target non-obvious members. The `!!r[idField]` filter drops malformed rows instead of emitting undefined-profile objects.
**Probe:** `test/invitation/invitation-repository.spec.ts:580–660` — POST stubbed `times: 1`, sent-list stubbed `{start:0,count:1,...}`, result asserted equal to the newest fixture row INCLUDING `.profile.entityUrn`/`.profileId` join (:628–655).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "linkedin-private-api", query: "sendInvitation normInvitations", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt send-then-read-back when a write API returns no body: cheapest reliable materialization of the created entity. Adapt the recency assumption to your concurrency model. Runner-up in-suite: linvo's connect-outreach verifies via DOM state; this is the API-side twin. Direct tests pin the whole flow including the profile join.
