<!-- capsule-v2 -->
# Guard rate-limit ladder — which four gates run before a comment is accepted?

**Source:** isso MIT `master@5ad388d9f10cc5227f6e5d901c249ca888f5ef72`; Codebase Memory `ext-isso`. **Question:** In what order does `Guard.validate` reject spam, and why does the reply-to-self check read "edit time frame"?

## Guard._limit ladder
**Path/Symbol:** `isso/db/spam.py:Guard.validate` → `_limit` (lines 16–72).
**Signature:** `validate(uri, comment) -> (bool, reason)`; `_limit(uri, comment) -> (bool, reason)`.
**Data Shape:** reads config keys `ratelimit`, `direct-reply`, `reply-to-self`, `require-email`, `require-author`; `self.max_age` = `[general] max-age`.

### Decisive source
```python
for func in (self._limit, self._spam):
    valid, reason = func(uri, comment)
    if not valid:
        return False, reason

# block more than :param:`ratelimit` comments per minute
rv = self.db.execute(
    ["SELECT id FROM comments WHERE remote_addr = ? AND ? - created < 60;"],
    (comment["remote_addr"], time.time())
).fetchall()
if len(rv) >= self.conf.getint("ratelimit"):
    return False, "{0}: ratelimit exceeded ..."
...
elif self.conf.getboolean("reply-to-self") is False:
    rv = self.db.execute(
        ["SELECT id FROM comments WHERE    remote_addr = ?", "AND id = ?", "AND ? - created < ?"],
        (comment["remote_addr"], comment["parent"], time.time(), self.max_age),
    ).fetchall()
    if len(rv) > 0:
        return False, "edit time frame is still open"
```

**Flow:** (1) per-IP 60-second count vs `ratelimit`; (2) top-level-only: direct replies to the post capped at `direct-reply` per IP (`parent IS NULL` branch); (3) reply-to-self blocked while the parent's edit window (`max-age`) is still open unless enabled; (4) require-email / require-author presence checks. `_spam` is a stub returning `(True, "")`.
**Invariant:** The reply-to-self rule is implemented as a TIME-WINDOW query on the parent authored by the same IP — the message names the edit window because that window IS the constraint; disabling `guard.enabled` short-circuits everything (`return True, ""`) — imports set this off deliberately.
**Probe:** `grep -cF 'SELECT id FROM comments WHERE remote_addr = ? AND ? - created < 60' isso/db/spam.py` (`1`); `grep -c 'AND parent IS NULL;' isso/db/spam.py` (`1`); `grep -c 'edit time frame is still open' isso/db/spam.py` (`1`).
**Test:** `isso/tests/test_guard.py:testRateLimit`, `testDirectReply`, `testSelfReply`, `testRequireEmail`, `testRequireAuthor`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-isso", query: "Guard validate ratelimit direct reply", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the ordered cheap→expensive ladder with first-failure return. Adapt thresholds to config names of your host. Omit `_spam` (empty extension point) or replace with your own checker in that slot.
