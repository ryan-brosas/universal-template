<!-- capsule-v2 -->
# latest via bounded deque — how do you take "last N" of an ascending stream without ORDER BY DESC?

**Source:** isso MIT `master@5ad388d9f10cc5227f6e5d901c249ca888f5ef72`; Codebase Memory `ext-isso`. **Question:** Why does `/latest` stream the whole mode-1 history through a deque?

## maxlen-N sliding window
**Path/Symbol:** `isso/views/comments.py:API.latest` (lines 1618–1658).
**Signature:** `comments = collections.deque(all_comments_gen, maxlen=limit)`.
**Data Shape:** generator from `fetchall(limit=None, order_by="created", mode="1")` (ascending); result projected onto a 12-field whitelist incl. thread `uri`.

### Decisive source
```python
if not self.conf.getboolean("latest-enabled"):
    return NotFound("Unavailable because 'latest-enabled' not set by site admin")
bad_limit_msg = "Query parameter 'limit' is mandatory (integer, >0)"
try:
    limit = int(request.args["limit"])
except (KeyError, ValueError):
    return BadRequest(bad_limit_msg)
...
all_comments_gen = self.comments.fetchall(limit=None, order_by="created", mode="1")
comments = collections.deque(all_comments_gen, maxlen=limit)
```

**Flow:** feature-flag gate (`[general] latest-enabled`) → mandatory positive integer limit → ascending full scan where the bounded deque keeps only the newest N in memory, preserving oldest→newest order on output → render each text and project fields.
**Invariant:** The endpoint is opt-IN per site (privacy: cross-thread comment listing is otherwise an enumeration oracle). Memory is O(limit) despite O(history) work — fine for isso scale; a porter at larger scale should push the window into SQL (`ORDER BY created DESC LIMIT n`) instead.
**Probe:** `grep -cF 'deque(all_comments_gen, maxlen=limit)' isso/views/comments.py` (exactly `1`).
**Test:** `isso/tests/test_comments.py:testLatestOk`, `testLatestWithoutLimit`, `testLatestBadLimitNaN/Negative/Zero`, `testLatestNotEnabled`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-isso", query: "latest enabled limit fetchall deque", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the deque window for small stores; adapt to SQL-side LIMIT when histories grow. Keep the explicit feature flag + strict limit validation — that's the privacy contract.
