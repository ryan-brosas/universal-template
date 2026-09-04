<!-- capsule-v2 -->
# Previously-approved-author fastpath — how do known-good commenters skip moderation?

**Source:** isso MIT `master@5ad388d9f10cc5227f6e5d901c249ca888f5ef72`; Codebase Memory `ext-isso`. **Question:** What exact query decides the WordPress-style "author must have a previously approved comment" bypass, and when is it applied?

## 6-month EXISTS probe
**Path/Symbol:** `isso/db/comments.py:Comments.is_previously_approved_author` (lines 148–169); consumer `isso/views/comments.py:new` (lines 435–441).
**Signature:** `is_previously_approved_author(email) -> bool`.
**Data Shape:** email may be `None` → immediate False (no check possible).

### Decisive source
```python
rv = self.db.execute(
    ["SELECT CASE WHEN EXISTS(",
     "    select * from comments where email=? and mode=1 and ",
     '    created > strftime("%s", DATETIME("now", "-6 month"))',
     ") THEN 1 ELSE 0 END;"],
    (email,),
).fetchone()
return rv[0] == 1
```
```python
with self.isso.lock:
    # if email-based auto-moderation enabled, check for previously approved author
    # right before approval.
    if self.approve_if_email_previously_approved and self.comments.is_previously_approved_author(data["email"]):
        data["mode"] = 1
    rv = self.comments.add(uri, data)
```

**Flow:** only consulted AFTER guard validation and only when `[moderation] approve-if-email-previously-approved` is on; flips this comment's mode from 2→1 just before insert, inside the same lock that performs the add — so notification extensions (`comments.new:after-save`) see the final mode.
**Invariant:** The window is a ROLLING 6 months of mode-1 comments by exact email match; NULL email never fast-paths. The check must run inside the write lock to prevent a mode flip racing another writer's moderation decision.
**Probe:** `grep -c 'created > strftime("%s", DATETIME("now", "-6 month"))' isso/db/comments.py` (exactly `1`).
**Test:** covered behaviorally by moderation flows in `isso/tests/test_comments.py` (no isolated unit — coverage caveat).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-isso", query: "is_previously_approved_author mode 1 approve", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt trust-window auto-approval for moderated comment systems. Adapt the window/match key. Omit the EXISTS spelling if your ORM has `.exists()` — but keep it inside the write lock.
