<!-- capsule-v2 -->
# Disqus import remap — how are string foreign-key comment trees relabeled on import?

**Source:** isso MIT `master@5ad388d9f10cc5227f6e5d901c249ca888f5ef72`; Codebase Memory `ext-isso`. **Question:** How does the Disqus importer translate dsq:id parent references into new integer ids while preserving order?

## Disqus.insert remap
**Path/Symbol:** `isso/migrate.py:Disqus.insert` (lines 67–81); orphans report (130–150).
**Signature:** `insert(thread, posts)`; per-post `remap[dsq_id] = rv["id"]`.
**Data Shape:** posts pre-sorted by `created` ascending; `item["parent"] = remap.get(item.pop("dsq:parent", None))`.

### Decisive source
```python
for item in sorted(posts, key=lambda k: k["created"]):
    dsq_id = item.pop("dsq:id")
    item["parent"] = remap.get(item.pop("dsq:parent", None))
    rv = self.db.comments.add(path, item)
    remap[dsq_id] = rv["id"]
self.comments.update(set(remap.keys()))
...
# deleted-without-children comments leave orphan rows; final GC:
self.db.comments._remove_stale()
```

**Flow:** chronological insertion guarantees a parent is inserted before any child that references it → single-pass remap of dsq ids to server-assigned integer ids → after all threads, `_remove_stale()` collapses tombstones whose children never arrived; remaining unreferenced exports are reported as named "orphans" with author/text preview and an `--empty-id` hint when NOTHING imported.
**Invariant:** Parent-before-child ordering is carried by the timestamp sort, not by graph traversal — malformed exports can still orphan, hence the post-pass GC + report rather than a crash. Deleted posts map to mode 4 tombstones so threading survives.
**Probe:** `grep -cF 'remap[dsq_id] = rv["id"]' isso/migrate.py` (`1`).
**Test:** `isso/tests/test_migration.py:test_disqus_empty_id`, `test_disqus_empty_id_workaround`, plus fixture disqus.xml.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-isso", query: "Disqus insert remap dsq thread", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt sort-then-remap for flat-keyed tree imports. Adapt sort key if timestamps unreliable (then topologically sort). Keep the terminal GC + human-readable orphan report.
