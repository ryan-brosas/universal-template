<!-- capsule-v2 -->
# Input verification + ACCEPT whitelist — what can a commenter actually submit?

**Source:** isso MIT `master@5ad388d9f10cc5227f6e5d901c249ca888f5ef72`; Codebase Memory `ext-isso`. **Question:** What are the exact validation rules and field-allowlist gates on comment creation and edit?

## API.verify + ACCEPT/FIELDS
**Path/Symbol:** `isso/views/comments.py:API.verify` (265–293); class constants FIELDS/ACCEPT (155–174); application in `new` (381–404).
**Signature:** `verify(comment) -> (bool, reason)`; `ACCEPT = {text, author, website, email, parent, title, notification}`; `FIELDS` = the 13 public output fields.
**Data Shape:** text ≥3 chars after rstrip, all values ≤65535; email ≤254 (RFC 5321); website ≤254 AND Django-conform URL regex; parent int-or-null; author/email HTML-escaped quote=False, website escaped quote=True then scheme-normalized.

### Decisive source
```python
for key in ("text", "author", "website", "email"):
    if not isinstance(comment.get(key), (str, type(None))):
        return False, "%s must be a string or null" % key
for key, value in comment.items():
    if value and len(str(value)) > 65535:
        return False, f"{key} is too long (maximum length: 65535)"
if len(comment["text"].rstrip()) < 3:
    return False, "text is too short (minimum length: 3)"
...
# new():
for field in set(data.keys()) - API.ACCEPT:
    data.pop(field)                      # unknown input fields silently dropped
...
rv = self.comments.add(uri, data)
...
for key in set(rv.keys()) - API.FIELDS:  # output projection
    rv.pop(key)
```

**Flow:** strip non-whitelisted INPUT keys → defaults for absent optionals → verify() → escape author/email (quote=False keeps addresses intact) and website (quote=True since it lands inside href) → normalize website to http(s). The SAME whitelist pattern projects OUTPUT: internal columns (tid, remote_addr, voters, notification internals) never leave via API.FIELDS subtraction.
**Invariant:** Input allowlist + output denylist are separate sets with different purposes — collapsing them leaks remote_addr. Verification returns reasons instead of raising so callers map them to 400s.
**Probe:** anchor `grep -n 'def verify' isso/views/comments.py | wc -l` (`1`); `grep -c '"text is too short' isso/views/comments.py | wc -l` (`1`).
**Test:** `isso/tests/test_comments.py:testVerifyFields`, `testWebsiteXSSPayloadIsEscaped`, `testUpdateWebsiteXSSPayloadIsEscaped`, `testVisibleFields`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-isso", query: "API verify ACCEPT FIELDS escape normalize", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt dual-set field governance and reason-returning validation. Adapt limits. Keep per-field escaping policy — uniform quote settings break emails or open XSS.
