<!-- capsule-v2 -->
# hidden_replies ledger — how does pagination arithmetic stay truthful across limit/offset?

**Source:** isso MIT `master@5ad388d9f10cc5227f6e5d901c249ca888f5ef72`; Codebase Memory `ext-isso`. **Question:** What exact formula produces `hidden_replies`, and why do nested fetches reset offset to 0?

## Count-minus-shown-minus-offset
**Path/Symbol:** `isso/views/comments.py:API.fetch` (lines 1020–1071).
**Signature:** `hidden_replies = reply_counts[root_id] - len(root_list) - args["offset"]`.
**Data Shape:** `reply_counts` = dict from `Comments.reply_count(uri)` keyed by parent id (None key = top-level bucket).

### Decisive source
```python
reply_counts = self.comments.reply_count(uri)
if args["limit"] == 0:
    root_list = []
else:
    root_list = list(self.comments.fetch(**args))
if root_id not in reply_counts:
    reply_counts[root_id] = 0
total_replies = sum(reply_counts.values()) if root_id is None else reply_counts[root_id]
...
rv = {
    "id": root_id,
    "total_replies": total_replies,
    "hidden_replies": reply_counts[root_id] - len(root_list) - args["offset"],
    ...
}
# nested level:
args["offset"] = 0   # Reset offset to 0 for nested comments to ensure correct pagination
replies = list(self.comments.fetch(**args))
...
comment["hidden_replies"] = comment["total_replies"] - len(replies)
```

**Flow:** one grouped COUNT query answers every `total_replies` without per-comment queries → root list fetched with caller limit/offset → hidden = count − shown − skipped → nested fetch reuses the same args dict but MUST zero the offset or page N of the root would silently drop nested replies.
**Invariant:** `total_replies` is mode-masked truth from SQL; `hidden_replies` is DERIVED arithmetic, never a second query. The shared-args mutation (`args["parent"]=...; args["limit"]=...; args["offset"]=0`) is the trap — porters who copy args must deep-copy or reset explicitly.
**Probe:** `grep -nF 'args["offset"]' isso/views/comments.py | grep -c hidden_replies` (exactly `1`: the formula line).
**Test:** `isso/tests/test_comments.py:testGetLimited`, `testGetWithOffset`, `testGetNestedWithOffset`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-isso", query: "reply_count hidden_replies total_replies offset", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt single-grouped-count + derived-hidden arithmetic. Adapt field names. Keep the offset-reset invariant if you reuse a params object across nesting levels.
