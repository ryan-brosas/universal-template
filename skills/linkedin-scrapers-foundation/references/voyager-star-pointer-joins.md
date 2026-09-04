<!-- capsule-v2 -->
# Voyager `*field` pointer-reference grammar — how do normalized-JSON documents reference sibling entities, and what does a porter have to unwrap before joining?

**Source:** linkedin-private-api MIT `master@e083f37`; Codebase Memory `linkedin-private-api`. **Question:** When a LinkedIn voyager payload field starts with `*`, what is it pointing at, and which unwraps must run before an `included[]` join can succeed?

## The star-pointer grammar and its three join shapes
**Path/Symbol:** `src/repositories/conversation.repository.ts:participantToProfileId` (:11), `src/repositories/message.repository.ts:participantToProfileId` (:14–15), `src/repositories/invitation.repository.ts:TO_MEMBER_FIELD/FROM_MEMBER_FIELD` (:10–11) consumed at (:28/:29), `src/repositories/profile.repository.ts:getProfilesFromResponse` (:20–27).
**Signature:** `(participant: string): string` — `participant.replace(/urn:li:fs_messagingMember:\(|\)/g, '').split(',')[1]`.
**Data Shape:** Pointer fields are string URNs prefixed with `*`: `'*participants': ['urn:li:fs_messagingMember:(12345,profile-id)', …]`, `'*from'/'*toMember'/'*fromMember': 'urn:li:fs_miniProfile:<uuid>'`. The referenced DEFINITIONS live in the same envelope's `included[]`, keyed by their own `entityUrn` (the pointer value minus the `*`-convention, i.e. the plain URN string).

### Decisive source
```ts
// conversation.repository.ts:11 / message.repository.ts:14-15
const participantToProfileId = (participant: string) =>
  participant.replace(/urn:li:fs_messagingMember:\(|\)/g, '').split(',')[1];
// → 'urn:li:fs_messagingMember:(12345,abc)' yields 'abc', which keys profiles[...] built by:
// profile.repository.ts:17  profileId: (miniProfile.entityUrn || '').replace('urn:li:fs_miniProfile:', '')

// invitation.repository.ts:14-31 — direction-dependent join field, chosen by endpoint
const results = response.included || [];
const profiles = keyBy(getProfilesFromResponse<T>(response), 'entityUrn');   // :20 RE-KEYS to full URNs
const invitations = results.filter(r => r.$type === INVITATION_TYPE && !!r[idField]);
return orderBy(
  invitations.map(invitation => ({ ...invitation, profile: profiles[invitation[idField]] })),
  'sentTime', 'desc',
);
// fetchSent passes '*toMember'; fetchReceived passes '*fromMember'
```

**Flow:** envelope arrives (`data.elements` pointers + `included[]` definitions) → `$type`-filter picks the document family → for each pointer field, UNWRAP its URN grammar down to the join key (`messagingMember:(sender,id)` → second tuple slot; bare `fs_miniProfile:` urns strip their scheme prefix via the profile transform) → look up the pre-keyBy'd `included` map → spread the resolved entities back onto the row alongside new derived fields (`participants`, `conversationId`, `sentFrom`, `profile`) → order by the family's recency field (`lastActivityAt` conversations, `createdAt` messages, `sentTime` invitations, all desc).
**Invariant:** the pointer VALUE is not the key — each pointer grammar has its own unwrap, and the KEYED FORM must match the unwrap's output: messagingMember tuples strip down to BARE ids and join against the default `profileId`-keyed dict, while voyager pointer fields (`targetUrn`, `*toMember`/`*fromMember`, `hitInfo.jobPosting`, `companyDetails.company`) carry FULL `urn:li:...` URNs and require a RE-KEY by `'entityUrn'`; joining with the wrong form silently yields `undefined` (the hydration is undefined-safe by design, see included-envelope-hydration). Direction-dependent fields must be selected per ENDPOINT (sent→`*toMember`, received→`*fromMember`) — using one fixed field empties half the joins. Factories pin the exact grammars a porter must reproduce: `createMiniProfileId()` emits `` `urn:li:fs_miniProfile:${uuid}` ``, conversation fixtures build `urn:li:fs_messagingMember:(<number>,<profileId>)` strings, and conversation entityUrns are `` `urn:li:fs_conversation:${uuid}` `` stripped by `transformConversationId`.

### Join-key form duality — which `keyBy` wins per join site
| Join site | Keyed form | Pointer consumed | Source |
|---|---|---|---|
| `getProfilesFromResponse` | `profileId` (stripped) — the DEFAULT output | — | `profile.repository.ts:27` |
| conversations `fetchConversations` | consumes default as-is | `*participants[]` → `participantToProfileId` → bare id | `conversation.repository.ts:69→25` |
| messages `fetchMessages` | consumes default as-is | `*from` → `participantToProfileId` → bare id | `message.repository.ts:51→56` |
| search `fetchPeople` | **re-keys** `keyBy(profiles, 'entityUrn')` | `searchHit.targetUrn` (full miniProfile URN) | `search.repository.ts:147→154` |
| invitations `parseInvitationResponse` | **re-keys** `keyBy(profiles, 'entityUrn')` | `invitation['*toMember'\|'*fromMember']` (full URN) | `invitation.repository.ts:20→26` |
| search `fetchCompanies` | keys TRANSFORMED companies by `'entityUrn'` | `searchHit.targetUrn` | `search.repository.ts:181→188` |
| search `fetchJobs` | two RAW keyBys by `'entityUrn'` | `hitInfo.jobPosting` → `companyDetails.company` two-hop | `search.repository.ts:213–214→217–218` |

Rule: pick the keyed form from the POINTER's grammar (tuple pointers → stripped ids; plain voyager URN pointers → full URNs), never from the entity type.

**Probe:** direct tests pin every hop: `test/conversation/conversation-repository.spec.ts` builds real messagingMember pointers and asserts the FULL round-trip in TWO suites — "should populate participants profile on the result conversations" (:123–137, scroller path) and "should add participants to the result conversation" (:314–329, direct-get path) — each asserting `.entityUrn` AND `.profileId` for participants[0] AND participants[1] (4 asserts ×2); `test/invitation/invitation-repository.spec.ts` read-back pins direction joins; NOTE the invitation specs' sort assertions compare against `orderBy(…, 'createdAt', 'desc')` (:72/:343) although invitation rows carry only `sentTime` — lodash treats all keys as undefined so the assert degenerates to a stability check; porters must NOT copy that assert shape (sort by the family's real recency field, as the repository source does).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "linkedin-private-api", query: "participantToProfileId messagingMember participants replace", limit: 5 });
// resolves BOTH twins: message.repository.ts :14-15 and conversation.repository.ts :11 (-19.97)
await mcp.codebase_memory.search_graph({ project: "linkedin-private-api", query: "parseInvitationResponse TO_MEMBER_FIELD FROM_MEMBER_FIELD", limit: 5 });
```

## Verdict
Adopt the `*field` = pointer-reference convention with per-grammar unwraps and transformed-key joins whenever porting any normalized-JSON LinkedIn surface; adapt the exact URN schemes to the endpoints you call (grammars drift by product area); omit none of the unwraps — skipping the messagingMember tuple-split or the direction-dependent member field produces silent empty joins rather than errors. Coverage: check_index_coverage stdin-JSON on all cited paths `no_recorded_issue`+`metadata_match` @ gen 2026-08-23T00:12:08Z; graph anchors resolve line-exact ×2. Companion to `included-envelope-hydration` (which owns filter→transform→keyBy) — THIS capsule owns the POINTER-side grammar the hydration consumes.
