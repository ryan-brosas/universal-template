<!-- capsule-v2 -->
# Edit-cookie shape guard — how is a per-comment edit token validated without trusting its payload?

**Source:** isso MIT `master@5ad388d9f10cc5227f6e5d901c249ca888f5ef72`; Codebase Memory `ext-isso`. **Question:** Why does `unsign_edit_cookie` check list-ness and length before indexing, and why is sha1(text) re-verified at edit AND delete?

## Shape-check + content checksum
**Path/Symbol:** `isso/views/comments.py:API.unsign_edit_cookie` (lines 243–263); consumers `edit` (:586–594) and `delete` (:675–684).
**Signature:** `unsign_edit_cookie(request, id) -> list[id, checksum]`; raises Forbidden on any failure.
**Data Shape:** cookie name = str(comment id); payload = `[id, sha1hex(text)]`; signer shared with admin-session/unsubscribe/moderation tokens.

### Decisive source
```python
rv = self.isso.unsign(request.cookies.get(str(id), ""))
except (SignatureExpired, BadSignature):
    raise Forbidden
if not isinstance(rv, list) or len(rv) != 2:
    raise Forbidden          # wrong-shape payload must be rejected, not indexed into
if rv[0] != id:
    raise Forbidden

# verify checksum, mallory might skip cookie deletion when he deletes a comment
if rv[1] != sha1(item["text"]):
    raise Forbidden
```

**Flow:** unsign with default max-age → shape-check (`isinstance(list)` + `len==2`) because the SAME serializer signs dicts (admin `{"logged": True}`) and tuples (unsubscribe); an attacker holding a validly-signed value of the wrong type must not crash or pass → id-match → then compare the cookie's text checksum against the CURRENT stored text so a stale cookie can't resurrect edited/deleted content.
**Invariant:** Cookie grants are bound to (comment id, exact text revision, 15-min window). Any of: wrong id, expired signature, non-list payload, mismatched checksum ⇒ 403. The docstring records the reasoning — keep it with the code.
**Probe:** `grep -cF 'sha1(item["text"])' isso/views/comments.py` (exactly `2`: edit + delete).
**Test:** `isso/tests/test_comments.py:testCookieOfWrongTypeIsRejected`, `testEditCookieForMissingCommentIsRejected`, `testUpdateForbidden`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-isso", query: "unsign_edit_cookie Forbidden sha1", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt shape-before-index on shared-signer payloads + content-revision checksums for edit tokens. Adapt checksum to your storage (sha1 fine for change detection, not secrecy). Omit nothing from the Forbidden ladder.
