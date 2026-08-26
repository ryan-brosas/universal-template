<!-- capsule-v2 -->
# SMTP reply-notification fanout — who gets notified and how are duplicates suppressed?

**Source:** isso MIT `master@5ad388d9f10cc5227f6e5d901c249ca888f5ef72`; Codebase Memory `ext-isso`. **Question:** Which comments receive reply notifications for a new post, and what are the exclusion rules?

## notify_users fanout
**Path/Symbol:** `isso/ext/notifications.py:SMTP.notify_users` (lines 150–170); admin path `notify_new` (136–145).
**Signature:** `notify_users(thread, comment) -> None`; audience = parent comment + ALL mode-1 siblings of the new comment's parent.
**Data Shape:** dedupe via `notified: list[email]`; requires per-recipient `notification` flag truthy.

### Decisive source
```python
parent_comment = self.isso.db.comments.get(comment["parent"])
comments_to_notify = [parent_comment] if parent_comment is not None else []
comments_to_notify += self.isso.db.comments.fetch(thread["uri"], mode=1, parent=comment["parent"])
for comment_to_notify in comments_to_notify:
    email = comment_to_notify["email"]
    if (
        "email" in comment_to_notify
        and comment_to_notify["notification"]
        and email not in notified
        and comment_to_notify["id"] != comment["id"]
        and email != comment["email"]
    ):
        ...
        self.sendmail(subject, body, thread, comment, to=email, headers=headers)
        notified.append(email)
```

**Flow:** only fires when `reply-notifications` enabled AND the new comment HAS a parent; audience = the parent being replied to plus every published sibling reply (depth-1 model) that opted in via `notification=1`. Excludes: missing email, opted-out rows, already-notified addresses, the new comment itself, and SELF-replies by email equality.
**Invariant:** Admin mail (`notify_new`) goes to `[smtp] to` for every new comment regardless of mode; USER mail only when `comment["mode"] == 1` — pending (mode 2) comments notify nobody until activation (`notify_activated`). Dedupe list prevents one address receiving N copies when it authored several sibling replies.
**Probe:** `grep -cF 'email != comment["email"]' isso/ext/notifications.py` (`1`).
**Test:** exercised indirectly through view flows (SMTP send path untested offline — coverage caveat).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-isso", query: "notify_users comments_to_notify notification parent", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt opt-in + self-exclusion + cross-run dedupe on fanout. Adapt audience definition if your threading differs. Omit nothing in the five-condition guard.
