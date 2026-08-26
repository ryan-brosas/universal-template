<!-- capsule-v2 -->
# WordPress import fixpoint — how are WP comment trees inserted when parents may follow children?

**Source:** isso MIT `master@5ad388d9f10cc5227f6e5d901c249ca888f5ef72`; Codebase Memory `ext-isso`. **Question:** What algorithm inserts WXR comments whose XML order is arbitrary, and what is the bail-out?

## WordPress.insert worklist
**Path/Symbol:** `isso/migrate.py:WordPress.insert` (lines 169–201); newline→break preprocessing `_process_comment_content` (220–227).
**Signature:** `while comments:` scan for insertable item; `else: return` bail.
**Data Shape:** ids set = original WP ids not yet inserted; remap = WP id → new DB id.

### Decisive source
```python
comments.sort(key=lambda k: k["id"])
remap = {}
ids = set(c["id"] for c in comments)
...
while comments:
    for i, item in enumerate(comments):
        if item["parent"] in ids:
            continue                      # parent not yet inserted -> defer
        item["parent"] = remap.get(item["parent"], None)
        rv = self.db.comments.add(path, item)
        remap[item["id"]] = rv["id"]
        ids.remove(item["id"])
        comments.pop(i)
        break
    else:
        # should never happen, but... it's WordPress.
        return
```

**Flow:** repeatedly sweep the remaining list inserting any comment whose parent is either absent-from-export (`None` root) or already inserted; each insertion unlocks its children on later sweeps. If a full sweep inserts nothing (cycle or dangling parent — corrupt export), the function silently abandons the REMAINDER of that thread rather than looping forever.
**Invariant:** Progress is monotonic; the for-else is the termination proof. Comment text gets `\n` → `"  \n"` (markdown hard break) except at boundaries, preserving WP's visual line breaks after markdown rendering.
**Probe:** `grep -c 'should never happen' isso/migrate.py` (`1`).
**Test:** `isso/tests/test_migration.py:test_wordpress` (fixture wordpress.xml).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-isso", query: "WordPress insert remap comments pop parent", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt deferred-worklist insertion for parent-optional imports. Adapt the bail to logging if silence is unacceptable. Keep the newline-hard-break preprocessing — it's why imported WP threads don't collapse into one paragraph.
