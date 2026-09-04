<!-- capsule-v2 -->
# Moderation token twins — how do emailed moderation links stay valid for months?

**Source:** isso MIT `master@5ad388d9f10cc5227f6e5d901c249ca888f5ef72`; Codebase Memory `ext-isso`. **Question:** Why do unsubscribe and moderate use `max_age=2**32` while edit cookies expire in 15 minutes?

## Long-lived action tokens
**Path/Symbol:** `isso/views/comments.py:unsubscribe` (line 736) and `moderate` (line 814).
**Signature:** `self.isso.unsign(key, max_age=2**32)` — ~136-year validity.
**Data Shape:** moderate payload = raw comment id (`sign(comment["id"])`, minted in notifications/Stdout); unsubscribe payload = `("unsubscribe", email)` tuple.

### Decisive source
```python
# unsubscribe
rv = self.isso.unsign(key, max_age=2**32)
if not isinstance(rv, list) or len(rv) != 2:
    raise Forbidden
if rv[0] != "unsubscribe" or rv[1] != email:
    raise Forbidden

# moderate
id = self.isso.unsign(key, max_age=2**32)
item = self.comments.get(id)
```

**Flow:** links embedded in notification emails must survive arbitrary delay before the admin clicks them → same signer as everything else but with an effectively unlimited max-age; the unsubscribe path compensates for the loose token by verifying BOTH payload slots (literal tag AND that the email in the URL matches the signed one).
**Invariant:** Token lifetime is a per-endpoint policy, not a global signer property. Moderate tokens are single-field (id) so the GET confirm modal re-presents the action before POST executes; unsubscribe tokens are two-field and self-describing to prevent confusion with edit-cookie payloads of shape `[id, checksum]`.
**Probe:** `grep -cE 'max_age=2\*\*32' isso/views/comments.py` (exactly `2`).
**Test:** `isso/tests/test_comments.py:testModify` (moderation key lifecycle).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-isso", query: "moderate unsign key max_age", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt per-endpoint max-age over one shared TTL. Adapt payload arity/tagging to your action set — always include a type literal when multiple shapes share a signer.
