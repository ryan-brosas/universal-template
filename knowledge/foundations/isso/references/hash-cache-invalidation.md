<!-- capsule-v2 -->
# Author-hash cache invalidation — why is the anonymized author hash deleted on delete?

**Source:** isso MIT `master@5ad388d9f10cc5227f6e5d901c249ca888f5ef72`; Codebase Memory `ext-isso`. **Question:** Where is the per-author `hash` computed, cached, and evicted — and what key does it use?

## email-or-remote_addr hash
**Path/Symbol:** `isso/views/comments.py:API._process_fetched_list` (lines 1085–1105); eviction in `delete` (:686) and `moderate` (:877); mint in `new` (:449–451).
**Signature:** `key = item["email"] or item["remote_addr"]`; `self.hash = hasher.uhash` (configurable algorithm, default sha1, salted).
**Data Shape:** cache namespace `"hash"`, key = utf-8 bytes of the email/IP string, value = hex digest; `remote_addr` already anonymized (/24,/48) by `utils.anonymize`.

### Decisive source
```python
# _process_fetched_list
val = self.cache.get("hash", key.encode("utf-8"))
if val is None:
    val = self.hash(key)
    self.cache.set("hash", key.encode("utf-8"), val)
item["hash"] = val

# delete / moderate-delete:
self.cache.delete("hash", (item["email"] or item["remote_addr"]).encode("utf-8"))
```

**Flow:** on create and on every fetch the hash is memoized under namespace `"hash"`; when a comment is deleted (either path) the author's cached hash is EVICTED so the next fetch recomputes against current config (algorithm/salt may have changed). Gravatar URLs are separate: md5 of email-or-AUTHOR (`_add_gravatar_image`), never cached.
**Invariant:** Hash identity = (salt, algorithm, key); because config can change at runtime restart, cache entries must be treated as disposable — hence delete-on-delete instead of update. The uhash layer enforces str-in/hex-str-out and raises TypeError on bytes to keep call sites honest.
**Probe:** `grep -cF 'self.cache.delete("hash"' isso/views/comments.py` (exactly `2`).
**Test:** `isso/tests/test_comments.py:testHash`, `testVisibleFields` (FIELDS whitelist strips internal columns like remote_addr before JSON).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-isso", query: "cache hash email remote_addr uhash", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt namespaced memoization + explicit eviction on identity-relevant mutations. Adapt digest choice. Keep remote_addr out of API payloads — hash-only exposure is the privacy contract.
