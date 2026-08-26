<!-- capsule-v2 -->
# Title-fetch on thread creation — what happens when the first comment lands on an unknown URI?

**Source:** isso MIT `master@5ad388d9f10cc5227f6e5d901c249ca888f5ef72`; Codebase Memory `ext-isso`. **Question:** How is a thread's title obtained, and why must the whole check-and-create run under the app lock?

## curl-back title resolution
**Path/Symbol:** `isso/views/comments.py:API.new` (lines 409–425); parser `isso/utils/parse.py:thread` (lines 9–70).
**Signature:** `with http.curl("GET", local("origin"), uri) as resp:` → `parse.thread(resp.read(), id=uri)` → `(id, title)`.
**Data Shape:** `local("origin")` = request Origin/Referer validated against `[general] host` list (wsgi.origin); `parse.thread` returns `(data-isso-id|id, data-title|h1-text|"Untitled.")`.

### Decisive source
```python
with self.isso.lock:
    if uri not in self.threads:
        if not data.get("title"):
            with http.curl("GET", local("origin"), uri) as resp:
                if resp and resp.status == 200:
                    uri, title = parse.thread(resp.read(), id=uri)
                else:
                    return BadRequest(
                        f"Cannot create new thread: URI {uri} is not accessible and no title was provided. ...")
        else:
            title = data["title"]
        thread = self.threads.new(uri, title)
```

**Flow:** unknown URI + no client title → fetch the PAGE from the validated origin and scrape the nearest-h1-to-#isso-thread (or `data-title`) → still unreachable ⇒ explicit BadRequest telling the caller to pass `title`. The lock spans contains-check through `threads.new`, so two concurrent first-comments can't both create the thread.
**Invariant:** Thread identity can be REWRITTEN by the page itself (`parse.thread` may return a different id via `data-isso-id`) — comments always land on the canonical id. Title scraping only ever talks to hosts in the configured allowlist.
**Probe:** `grep -cF 'http.curl("GET", local("origin"), uri)' isso/views/comments.py` (exactly `1`); `grep -c data-title isso/utils/parse.py` (`1`).
**Test:** `isso/tests/test_comments.py:testTitleNull` (explicit-title path); `testCreateInvalidThreadForParent`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-isso", query: "threads.new parse.thread title origin", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt server-side title discovery with explicit fallback error naming the missing parameter. Adapt scraper to your DOM conventions. Omit cross-host fetching — origin validation is non-negotiable.
