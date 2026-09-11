<!-- capsule-v2 -->
# Feed conditional requests — how does the Atom feed leverage etags without a cache table?

**Source:** isso MIT `master@5ad388d9f10cc5227f6e5d901c249ca888f5ef72`; Codebase Memory `ext-isso`. **Question:** What identifies feed freshness and how is 304 negotiated?

## RSS view etag
**Path/Symbol:** `isso/views/comments.py:API.feed` (lines 1266–1363).
**Signature:** `response.set_etag("{tid}-{id}".format(**comment0))`; `response.last_modified = comment0["modified"] or comment0["created"]`; `return response.make_conditional(request)`.
**Data Shape:** `comment0` = FIRST item of the newest-first fetch (`asc=0`, limit = max(query limit, `[rss] limit`) — note the query param can only RAISE the configured cap).

### Decisive source
```python
# Add an etag/last-modified value for caching purpose
if comment0 is None:
    response.set_etag("empty")
    response.last_modified = 0
else:
    response.set_etag("{tid}-{id}".format(**comment0))
    response.last_modified = comment0["modified"] or comment0["created"]
return response.make_conditional(request)
```

**Flow:** newest comment's (tid,id) IS the feed version vector — any newer comment changes the tuple, invalidating client caches; empty feeds pin etag "empty" + epoch mtime so even empty threads cache coherently. `make_conditional` turns If-None-Match/If-Modified-Since into 304 with no body rebuild (the XML was already built — werkzeug just skips the payload).
**Invariant:** Feature-gated on `[rss] base` (404 when unset); entry ids use tag-URIs `tag:{hostname},2018:/isso/{tid}/{id}` with thr:in-reply-to for parents. Updated timestamps fall back created→modified per entry and the FEED-level updated uses the first (newest) entry or fixed 1970 date.
**Probe:** anchor `grep -c 'set_etag' isso/views/comments.py | wc -l` (`1`).
**Test:** `isso/tests/test_comments.py:testFeed`, `testFeedEmpty`, `testNoFeed`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-isso", query: "feed atom set_etag make_conditional rss", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt head-item-derived validators for derived documents. Adapt to your framework's conditional helpers. Keep the empty-feed sentinel — it prevents 304-storms on brand-new threads.
