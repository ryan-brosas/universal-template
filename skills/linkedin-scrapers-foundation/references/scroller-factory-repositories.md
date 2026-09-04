<!-- capsule-v2 -->
# Scroller-factory repositories — public methods return live scroller objects, not arrays (how do I design a scraper API that pages without exposing pagination to callers)?

**Source:** linkedin-private-api MIT `master@e083f37`; Codebase Memory `linkedin-private-api`. **Question:** What object shape lets a client library expose "get all people/messages/invitations" ergonomics while keeping cursor state internal?

## The factory pattern
**Path/Symbol:** `src/repositories/search.repository.ts:searchPeople` (:30–48) + twins `searchCompanies/searchOwnConnections/searchConnectionsOf/searchJobs`; `message.repository.ts:getMessages` (:24–26); `conversation.repository.ts:getConversations` (:53–58); `invitation.repository.ts:getSentInvitations/getReceivedInvitations` (:43–57).
**Signature:** `searchPeople({skip = 0, limit = 10, filters = {}, keywords} = {}): PeopleSearchScroller` — returns a scroller constructed with `fetchPeople: this.fetchPeople.bind(this)`.
**Data Shape:** scroller holds ONLY config (skip/limit/filters/keywords) + the bound fetch closure; zero response data until `scrollNext()` is awaited.

### Decisive source
```ts
searchPeople({ skip = 0, limit = 10, filters = {}, keywords }: {...} = {}): PeopleSearchScroller {
  return new PeopleSearchScroller({
    skip, limit, filters, keywords,
    fetchPeople: this.fetchPeople.bind(this),
  });
}
// derived variants are FILTER REWRITES over the same fetcher:
searchOwnConnections({...filters, network: LinkedInNetworkType.F})            // :82
searchConnectionsOf({profileId, ...: {...filters, connectionOf: profileId, network: F}})  // :104
```

**Flow:** caller gets a lazy handle immediately → each `.scrollNext()` invokes the private bound fetch with the scroller's CURRENT skip/limit → the repository's fetch does envelope hydration (see included-envelope-hydration) and returns typed rows → the abstract base mutates its own cursor. Convenience methods are pure filter injections (`network: 'F'`, `connectionOf`) — ONE wire call path serves four public APIs.
**Invariant:** the fetch closure is `.bind(this)`-bound at construction so scrollers stay decoupled from repository lifetime; defaults (`skip=0, limit=10`; invitations `limit=100`) live in BOTH factory and scroller ctor signatures consistently; nothing async happens in the factory itself.
**Probe:** `test/search/search-repository.spec.ts:126–207` drives three scrollNext pages through mocked axios start=0/10/20 and overrides `{skip:100, limit:1}` → 100/101/102; `test/message/message-repository.spec.ts:24–45` pins getMessages→MessageScroller wiring.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "linkedin-private-api", query: "SearchRepository searchPeople scroller", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt for any client library over a paged API: factories return stateful iterators, convenience methods are filter rewrites, fetchers stay private+bound. Adapt default page sizes per endpoint budget. Omit nothing. Direct tests pin paging math end-to-end; this is the repo's second big architectural idea after envelope hydration.
