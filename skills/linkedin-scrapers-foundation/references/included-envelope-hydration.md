<!-- capsule-v2 -->
# Included-envelope hydration — how do I turn a Voyager `data/*` + `included[]` response into typed domain objects?

**Source:** linkedin-private-api MIT `master@e083f37` (`e083f370c331ed643348158b8c64f905de477626`); Codebase Memory `linkedin-private-api`. **Question:** Every private-API endpoint answers in LinkedIn's normalized-JSON envelope (hits in `data.elements`, payloads in `included[]`) — what is the deterministic recipe to join them into usable objects without hardcoding per-endpoint shapes?

## Shared hydration primitive (the whole trick)
**Path/Symbol:** `src/repositories/profile.repository.ts:getProfilesFromResponse` (:20–28) + helpers :11–18.
**Signature:** `getProfilesFromResponse<T extends { included: (LinkedInMiniProfile | { $type: string })[] }>(response: T): Record<ProfileId, MiniProfile>`.
**Data Shape:** input = any envelope with `included[]`; output = dict keyed by stripped `profileId` (`entityUrn.replace('urn:li:fs_miniProfile:', '')`). Picture URLs are DERIVED: `${picture.rootUrl}${artifact.fileIdentifyingUrlPathSegment}` per artifact (:11–12) — never stored as one URL.

### Decisive source
```ts
export const getProfilesFromResponse = <T extends { included: (LinkedInMiniProfile | { $type: string })[] }>(
  response: T,
): Record<ProfileId, MiniProfile> => {
  const miniProfiles = filter(response.included, p => p.$type === MINI_PROFILE_TYPE) as LinkedInMiniProfile[];
  const transformedMiniProfiles = miniProfiles.map((miniProfile: LinkedInMiniProfile) => transformMiniProfile(miniProfile));
  return keyBy(transformedMiniProfiles, 'profileId');
};
```

**Flow:** (1) FILTER `included[]` by exact `$type` constant (`com.linkedin.voyager.identity.shared.MiniProfile`, `...dash.identity.profile.Profile`, `...messaging.Event`, `...relationships.invitation.Invitation`, etc. — each entity file exports a `*_TYPE` const). (2) TRANSFORM each hit (strip URN prefixes, derive picture URLs). (3) KEY by a URN-derived id. (4) JOIN onto hits from the other half of the envelope: search hits join `profiles[searchHit.targetUrn]` (`src/repositories/search.repository.ts:147–155`), message events join `profiles[participantToProfileId(message['*from'])]` (`message.repository.ts:50–57`), invitations join `profiles[invitation['*toMember'|'*fromMember']]` (`invitation.repository.ts:20–27`), conversations resolve every `*participants[]` member through the same dict (`conversation.repository.ts:21–33`).

### Envelope contract
```ts
export interface LinkedInCollectionResponse<T, I, M = undefined> {
  data: { elements: T[]; $type: 'com.linkedin.restli.common.CollectionResponse'; entityUrn: string;
          paging: Paging /* { count, links, start } */; metadata?: M };
  included: I[];
}
```
(`src/entities/linkedin-collection-response.entity.ts`) — hits may also arrive as *clustered* `data.elements[].elements` (BlendedSearchCluster), which callers flatten before joining (`search.repository.ts:148–150`: `flatten(response.data.elements.filter(e => e.type === SEARCH_HITS && e.elements).map(e => e.elements!))`).

**Flow (join keys seen in this repo):** `targetUrn` (search hits → mini profiles/companies), `' *from'` messagingMember URN (events → sender), `'*toMember'/'*fromMember'` (invitations → counterparties), `'*participants'` (conversations → members), `hitInfo.jobPosting → companyDetails.company → keyedCompanies[urn]` (jobs → posting → base company, `search.repository.ts:216–232`).
**Invariant:** `$type` constants are compared EXACTLY against exported consts, never substrings; a missing counterpart yields `undefined` fields on the spread (e.g. `profile: profiles[targetUrn]` is undefined-safe) — the row survives, only its joined payload is missing. MessagingMember URNs must strip BOTH parens before splitting: `.replace(/urn:li:fs_messagingMember:\(|\)/g, '').split(',')[1]`.
**Probe:** `test/profile/get-profiles-from-response.spec.ts` + `test/profile/profile-repository.spec.ts:36–40` (`difference(Object.keys(resultProfile), Object.keys(profile)).length === 0` — output keeps ALL raw keys plus derived ones) and `test/search/search-repository.spec.ts:80–103` (targetUrn↔included.entityUrn join pinned end-to-end through a mocked axios).

### Exported `$type` constant registry (the full filter vocabulary)
Every entity file exports ONE wire-string const; hydration filters compare `p.$type === CONST` exactly. All nine at pin `e083f37`:

| Constant | Wire string | Defined | Consumed by (graph USAGE edges) |
|---|---|---|---|
| `MINI_PROFILE_TYPE` | `com.linkedin.voyager.identity.shared.MiniProfile` | `linkedin-mini-profile.entity.ts:5` | `getOwnProfile`, `getProfilesFromResponse` |
| `PROFILE_TYPE` | `com.linkedin.voyager.dash.identity.profile.Profile` | `linkedin-profile.entity.ts:4` | `ProfileRepository.getProfile` |
| `COMPANY_TYPE` | `com.linkedin.voyager.dash.organization.Company` | `linkedin-company.entity.ts:3` | `ProfileRepository.getProfile` |
| `BASE_COMPANY_TYPE` | `com.linkedin.voyager.organization.Company` | `linkedin-base-company.ts:3` | `SearchRepository.fetchJobs` |
| `MINI_COMPANY_TYPE` | `com.linkedin.voyager.entities.shared.MiniCompany` | `linkedin-mini-company.entity.ts:3` | `SearchRepository.fetchCompanies` |
| `JOB_POSTING_TYPE` | `com.linkedin.voyager.jobs.JobPosting` | `linkedin-job-posting.ts:1` | `SearchRepository.fetchJobs` |
| `CONVERSATION_TYPE` | `com.linkedin.voyager.messaging.Conversation` | `linkedin-conversation.entity.ts:21` | `ConversationRepository.fetchConversations` |
| `EVENT_TYPE` | `com.linkedin.voyager.messaging.Event` | `linkedin-event.entity.ts:3` | `MessageRepository.fetchMessages` |
| `INVITATION_TYPE` | `com.linkedin.voyager.relationships.invitation.Invitation` | `linkedin-invitation.entity.ts:13` | `parseInvitationResponse` (+ test factory) |

Porting traps the table encodes: (a) **dash vs non-dash company split** — `COMPANY_TYPE` is `dash.organization.Company` while `BASE_COMPANY_TYPE` is plain `organization.Company`; they answer DIFFERENT decorations (`ProfileRepository.getProfile` vs job-search included) — swapping them silently filters everything out; (b) `EVENT_TYPE` lives in the MESSAGING domain (`messaging.Event`), not an events product; (c) profile family splits `identity.shared.MiniProfile` (envelope workhorse) vs `dash.identity.profile.Profile` (dash decoration payloads).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "linkedin-private-api", query: "getProfilesFromResponse", limit: 10, fields: ["signature", "name", "file"] });
// trace_path --function-name getProfilesFromResponse --direction inbound → 14 callers across all five repositories/scrollers
```

## Verdict
Adopt the three-step recipe (filter-by-$type → transform → keyBy-URN) and the undefined-safe join: it works for ANY normalized-JSON API, not just LinkedIn. Adapt the `$type` constants and URN prefix strips per endpoint/decoration generation. Omit nothing — this is the repo's core reusable idea. Direct tests pin the join for people-search, messages, invitations, conversations; job/company joins are source-grounded only (factories cover happy path).
