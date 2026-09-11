<!-- capsule-v2 -->
# List-Unsubscribe header — how is a one-click unsubscribe URL built and signed?

**Source:** isso MIT `master@5ad388d9f10cc5227f6e5d901c249ca888f5ef72`; Codebase Memory `ext-isso`. **Question:** What exact token and URL shape power RFC-2369/8058 unsubscription?

## create_headers
**Path/Symbol:** `isso/ext/notifications.py:SMTP.create_headers` (lines 90–94); body twin in `format` (:127–131); endpoint `isso/views/comments.py:unsubscribe` (:732–766).
**Signature:** `create_headers(parent_comment, recipient) -> tuple[(header, value),]`.
**Data Shape:** key = `sign(("unsubscribe", recipient))`; URL = `{public-endpoint}/id/{parent_id}/unsubscribe/{quote(recipient)}/{key}`.

### Decisive source
```python
def create_headers(self, parent_comment, recipient):
    uri = self.public_endpoint + "/id/%i" % parent_comment["id"]
    key = self.isso.sign(("unsubscribe", recipient))
    return (("List-Unsubscribe", uri + "/unsubscribe/" + quote(recipient) + "/" + key),)
```

**Flow:** every notification email carries `List-Unsubscribe` pointing at the PARENT comment's unsubscribe route; the same URL is repeated as a plain-text footer link. The route handler re-checks the payload slots (`"unsubscribe"`, email equality with the URL's unquoted email) before flipping `notification=0`.
**Invariant:** The signed tuple is self-describing (tag first, recipient second) so it can't be replayed against other endpoints sharing the signer; the recipient is percent-encoded in the path but compared after `unquote`. Minted at exactly TWO sites (header + body) from one helper shape.
**Probe:** `grep -cF 'key = self.isso.sign(("unsubscribe", recipient))' isso/ext/notifications.py` (exactly `2`).
**Test:** no direct unit (mail-path coverage caveat); route behavior covered by view flows.

## Get live surrounding code
```ts
await mcp.codebase_memory.search_graph({ project: "ext-isso", query: "List-Unsubscribe unsubscribe sign recipient", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt self-describing signed action tokens for mail links. Adapt URL scheme. Keep the tag+payload tuple — it's what makes cross-endpoint replay impossible.
