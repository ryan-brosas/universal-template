<!-- capsule-v2 -->
# Voyager pagination loop — how do I page a count-capped API feed to exactly `limit` items without infinite loops?

**Source:** open-linkedin-api MIT `main@5feee360` (`Linkedin.search` :203–303, `get_profile_posts` :106–155, `get_post_comments` :157–201). Codebase Memory `open-linkedin-api`. **Question:** what loop structure handles both token pagination and start-offset pagination with the 49-count search ceiling and the ~1000-result wall?

## search() while-loop
**Path/Symbol:** `linkedin.py:Linkedin.search` (:203–303); class caps `_MAX_SEARCH_COUNT=49`, `_MAX_POST_COUNT=100`, `_MAX_REPEATED_REQUESTS=200` (:47–52); token variant `get_post_comments` (:181–200).
**Signature:** `search(params: Dict, limit=-1, offset=0) -> List`; `-1` = unbounded; loop shrinks `count` when close to the limit.
**Data Shape:** GraphQL-style `/graphql?variables=(start:N,…)` URL; response filtered through `_type` string checks (`com.linkedin.restli.common.CollectionResponse` → `SearchClusterViewModel` → `SearchItem` → `EntityResultViewModel`); comments variant pages via `metadata.paginationToken`.

### Decisive source
```python
while True:
    if limit > -1 and limit - len(results) < count:
        count = limit - len(results)              # fetch only the remainder near the limit
    ...
    results.extend(new_elements)
    if ((-1 < limit <= len(results)) \
        or len(results) / count >= Linkedin._MAX_REPEATED_REQUESTS) \
        or len(new_elements) == 0:
        break                                     # three exits: satisfied / safety-wall / dry page
```

**Flow:** build default params (`start = len(results)+offset`) → fetch → type-guard every nesting level (wrong `_type` ⇒ skip element) → extend results → exit on limit reached, on empty growth (end of feed), or on the `_MAX_REPEATED_REQUESTS` ratio wall (LinkedIn silently stops returning new results past ~1000; the wall turns that soft failure into a bounded stop).
**Invariant:** the empty-page exit (`len(new_elements) == 0`) must exist independently of the limit exit — LinkedIn keeps serving duplicate-filled pages after exhaustion; the comments variant adds an explicit "API returns empty elements past total" break (:195–198). Every page request still flows through the evade-pacing transport (see voyager-api-client.md).
**Probe:** no upstream tests for search — coverage caveat recorded. Graph anchors resolve: `Linkedin.search`, `get_post_comments`, `get_profile_posts`, `_fetch`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "open-linkedin-api", query: "search", limit: 5 });
```

## Verdict
Adopt the three-exit while-loop with remainder-shrunk counts and type-guarded element extraction; adapt endpoints/params and the wall constant to host; omit the hard-coded queryId (rotates). Caveat: source-grounded only; the ~1000-result wall is empirically encoded as `_MAX_REPEATED_REQUESTS`.
