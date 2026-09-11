<!-- capsule-v2 -->
# DocDetails merge algebra — how do metadata from conflicting providers merge without losing the newest truth?

**Source:** paper-qa (Apache-2.0) `main@57e89f72`; Codebase Memory `ext-paper-qa`. **Question:** When Crossref says one publication date and Semantic Scholar another, what are the EXACT per-field precedence rules for summing two DocDetails?

## Connected graph-selected seam
**Path/Symbol:** `src/paperqa/types.py:DocDetails.__add__` (:1267-1371), `__radd__`/`__iadd__` int-no-op routes (:1373-1383); consumed by `clients.DocMetadataClient.query` :197-199 (`sum(...)` over provider results!) and both post-processors (`retractions.py:79-83`, `journal_quality.py:72-80`).
**Signature:** `def __add__(self, other: DocDetails | int) -> DocDetails`.
**Data Shape:** Per-field rules: `other` dicts deep-merge with `bibtex_source`/`client_source` coerced to lists and concatenated; authors pick whichever list has MORE total chars; two non-null keys wipe to None (forces regeneration); `citation_count`/`year`/`publication_date` take max (None-dance preserves 0 as meaningful); differing content_hashes discard to None; everything else prefers non-null `other_value` UNLESS `PREFER_OTHER=False`.

### Decisive source
```python
PREFER_OTHER = True
if self.publication_date and other.publication_date:
    PREFER_OTHER = self.publication_date <= other.publication_date   # newer record wins
...
elif field == "key" and self_value is not None and other_value is not None:
    merged_data[field] = None          # conflicting keys → regenerate downstream
...
if merged_data["doi"] != self.doi or merged_data["content_hash"] != self.content_hash:
    merged_data["doc_id"] = compute_unique_doc_id(merged_data["doi"], merged_data.get("content_hash"))
return DocDetails(**merged_data)
```

**Flow:** Freshness gate (later-or-equal publication_date ⇒ prefer other) → per-field merge table → doc_id recomputed when doi/content_hash shifted. `__radd__` special-cases literal 0 so plain Python `sum(provider_results)` works — the aggregation idiom depends on it.
**Invariant:** Merge NEVER mutates inputs (fresh instance); `source_quality=0` ("predatory journal") must survive merges — that is why the numeric fields use an explicit None-dance instead of truthiness; retraction flag propagates because post-processors merge `is_retracted` through this operator with `doc_id`/`dockey` pinned.
**Probe:** `tests/test_paperqa.py::test_docdetails_merge_with_list_fields` (:2799), `::test_docdetails_merge_with_non_list_fields` (:2765), `::test_docdetails_doc_id_roundtrip` (:2892).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-paper-qa", query: "DocDetails __add__ merge bibtex_source client_source", limit: 10 });
```

## Verdict
Adopt the per-field precedence table and the sum()-compatible int route; adapt freshness to your timestamp field; omit author-char-length heuristic if your providers return equal-quality author lists. Direct tests upstream pin list/non-list merges.
