<!-- capsule-v2 -->
# Collection-response envelope — how do you type TEN different Voyager endpoints with ONE shape and join their payloads correctly?

**Source:** linkedin-private-api MIT `master@e083f37`; Codebase Memory `linkedin-private-api`. **Question:** what single data contract do all GET responses share, and where do hydrated entities actually live?

## One generic, ten instantiations
**Path/Symbol:** `src/entities/linkedin-collection-response.entity.ts:LinkedInCollectionResponse` (:7-16); instantiated by all 10 files in `src/responses/*`.
**Signature:** `interface LinkedInCollectionResponse<T, I, M = undefined>`.
**Data Shape:** `data: { elements: T[]; $type: 'com.linkedin.restli.common.CollectionResponse'; entityUrn: string; paging: { count: number; links: string[]; start: number }; metadata?: M }` plus a SIBLING top-level `included: I[]`.

### Decisive source
```ts
export interface LinkedInCollectionResponse<T, I, M = undefined> {
  data: {
    elements: T[];
    $type: 'com.linkedin.restli.common.CollectionResponse';
    entityUrn: string;
    paging: Paging;
    metadata?: M;
  };
  included: I[];
}
```

**Flow:** every endpoint response picks its own `<T, I, M>`: profiles use `GetProfileResponse = LinkedInCollectionResponse<ProfileUrn, LinkedInProfile | LinkedInCompany>` (profile.response.get.ts); blended search adds a rich M — `keywords, numVisibleResults, origin, searchId, totalResultCount, totalResultDisplayText` (blended-search.reponse.get.ts); received invitations carry M.`paginationToken` (received-invitations.response.get.ts); conversations carry M.`unreadCount` (conversations.response.get.ts); sent invitations carry M.`invitationType` (sent-invitations.response.get.ts). Hydration joins `data.elements` URNs against `included[]` — elements reference, included defines. Writes are typed DIFFERENTLY on purpose: `SendMessageResponse.data.$type = 'com.linkedin.restli.common.ActionResponse'` with a LITERAL `included: []` — a compile-time marker that POSTs carry nothing to hydrate (message.response.post.ts). Non-collection reads also break the mold: `GetOwnProfileResponse` has `'*miniProfile'` pointer + plainId + inline `included` (own-profile.response.get.ts), and single-conversation reads drop `data.elements` for a direct `data: LinkedinConversation` (conversation.response.get.ts).
**Invariant:** `elements`/`included` is a pointer/definition split — NEVER look for full entities inside `elements`; `paging.{count,start}` feeds skip-limit math while cursor endpoints may override it with M.`paginationToken`; M stays optional via the `= undefined` default so 1- and 2-param instantiations stay legal.
**Probe:** `test/profile/get-profiles-from-response.spec.ts` builds fixtures as `{ elements: [], …, included: createMiniProfile(count) }` and every mutation targets `response.included` (incl. setting `included = []` at :59) — pinning that hydration consumes `included` EXCLUSIVELY.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "linkedin-private-api", query: "LinkedInCollectionResponse", limit: 5 });
```

## Verdict
Adopt the envelope shape, the pointer/definition join discipline, and the empty-`included: []`-on-writes marker for ANY Restli/LI-style API. Adapt the per-endpoint M interfaces and entity unions. Omit LinkedIn `$type` strings verbatim. Coverage caveat: `check_index_coverage` = `no_recorded_issue`+`metadata_match` on the kernel file; probe is a real spec (fixture-level, not live-network).
