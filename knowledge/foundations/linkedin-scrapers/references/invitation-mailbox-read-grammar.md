<!-- capsule-v2 -->
# Invitation mailbox read grammar — sent and received invitations answer on TWO different views with TWO query grammars (why does my faithful port of the received-invitations call 400 on the sent side?)

**Source:** linkedin-private-api MIT `master@e083f37` (`e083f370c331ed643348158b8c64f905de477626`); Codebase Memory `linkedin-private-api`. **Question:** Which endpoints and params page the invitation mailbox, and why can't sent and received share one wire shape?

## Two views, asymmetric grammars
**Path/Symbol:** `src/requests/invitation.request.ts:getReceivedInvitations` (:27–37) + `getSentInvitations` (:39–50); defaults plumbed from `src/repositories/invitation.repository.ts:getSentInvitations/getReceivedInvitations` (`{skip = 0, limit = 100}`).
**Signature:** `getReceivedInvitations({skip=0, limit=100})` → GET `relationships/invitationViews` params `{start, count, q: 'receivedInvitation'}`; `getSentInvitations({skip=0, limit=100})` → GET `relationships/sentInvitationViewsV2` params `{start, count, invitationType: 'CONNECTION', q: 'invitationType'}`.
**Data Shape:** restli paging names `start`/`count` on the wire vs `skip`/`limit` in the TS API (1:1 rename at the request boundary); received view = direct SELECTOR grammar (plural view name, SINGULAR q value); sent view = TYPE-FILTER grammar (`q=invitationType` + verbatim token `CONNECTION`) on a V2-suffixed view with no V1 sibling in this client.

### Decisive source
```ts
getReceivedInvitations({ skip = 0, limit = 100 } = {}) {
  const queryParams = { start: skip, count: limit, q: 'receivedInvitation' };
  return this.request.get<GetReceivedInvitationResponse>('relationships/invitationViews', { params: queryParams });
}
getSentInvitations({ skip = 0, limit = 100 } = {}) {
  const queryParams = { start: skip, count: limit, invitationType: 'CONNECTION', q: 'invitationType' };
  return this.request.get<GetSentInvitationResponse>('relationships/sentInvitationViewsV2', { params: queryParams });
}
```

**Flow:** repository factories default `{skip:0, limit:100}` (10× the search repos' `limit=10`) →
InvitationScroller advances `skip += limit` per page → each fetch renames skip→start, limit→count →
both views answer in the standard normalized envelope even though invitations are relationship rows →
hydration runs through `parseInvitationResponse` with direction-dependent join fields
(`*toMember` sent / `*fromMember` received — see voyager-star-pointer-joins) ordered `sentTime desc`.
The WRITE side (`POST growth/normInvitations`, body-less) is send-then-verify-invitation's seam.
**Invariant:** the grammars are NOT interchangeable — sending `q=receivedInvitation` to the sent view,
or omitting `invitationType: 'CONNECTION'`, fails; the type token is a verbatim wire enum, not a
label. View names differ in version suffix by endpoint family, not by symmetry. Defaults live
identically in factory AND scroller ctor (`skip=0, limit=100`) so override paths stay consistent.
**Probe:** `test/invitation/invitation-repository.spec.ts` pins the EXACT stub pair —
`when(axios.get(new URL('relationships/sentInvitationViewsV2', linkedinApiUrl).toString(), { params: {start:0, count:100, invitationType:'CONNECTION', q:'invitationType'} }))` — plus override mapping
(`{...reqParams, start: skip, count: limit}` at :63) and sentTime-desc ordering assertion (:52).
Runner caveat: suite not executable in this checkout (no node_modules) — probe evidence is source+spec
text; check_index_coverage on both cited paths = no_recorded_issue/metadata_match.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "linkedin-private-api", query: "getReceivedInvitations getSentInvitations invitationType", limit: 6 });
```

## Verdict
Adopt per-view grammar tables for vendor mailbox-style reads: never assume selector-style and
type-filter styles unify, and keep wire names (start/count) out of your public API (skip/limit).
Adapt tokens to fresh captures (they rot). Omit nothing behavioral. Runner-up in-suite: none — this
is the only repo in the foundation modeling both mailbox directions on distinct views.
