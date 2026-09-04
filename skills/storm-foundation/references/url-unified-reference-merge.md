<!-- capsule-v2 -->
# URL-unified reference merge — how do per-section local citation numbers become one global bibliography?

**Source:** storm MIT `main@fb951af7`; Codebase Memory `storm`. **Question:** When each section was written against its own `[1..k]` list, how do you merge them into a single reference table keyed by URL?

## Connected graph-selected seam
**Path/Symbol:** `knowledge_storm/storm_wiki/modules/storm_dataclass.py:StormArticle._merge_new_info_to_references` (:174-207) + `update_section` (:249-299).
**Signature:** `_merge_new_info_to_references(new_info_list: List[Information], index_to_keep: Optional[List[int]] = None) -> Dict[int, int]` (section-local idx → unified idx).
**Data Shape:** `self.reference = {"url_to_unified_index": {url: int}, "url_to_info": {url: Information}}`; unified index starts at 1; snippets of repeated URLs are unioned via `list(set(...))`.

### Decisive source
```python
if url not in self.reference["url_to_unified_index"]:
    self.reference["url_to_unified_index"][url] = (
        len(self.reference["url_to_unified_index"]) + 1)   # 1-based sequential mint
    self.reference["url_to_info"][url] = storm_info
else:
    existing_snippets = self.reference["url_to_info"][url].snippets
    existing_snippets.extend(storm_info.snippets)
    self.reference["url_to_info"][url].snippets = list(set(existing_snippets))
citation_idx_mapping[idx + 1] = self.reference["url_to_unified_index"][url]
```

**Flow:** `generate_article` runs sections in parallel → each section's LLM output carries ITS OWN local numbers → `update_section` first strips any `[i]` with `i > len(info_list)` (hallucinated refs, :271-280), drops unused infos from the merge via `index_to_keep`, then merges: new URL mints the next index, known URL folds snippets and reuses its index → section text is rewritten through the two-phase placeholder mapper → after ALL sections land, `post_processing()` calls `reorder_reference_index()` which renumbers by first appearance in reading order (pre-order traversal) and deletes never-cited URLs.
**Invariant:** (1) The URL is the sole identity for references — two Information objects with different snippets but the same URL share one bibliography entry. (2) Local numbering is 1-based because the writer prompt shows `[idx+1]` labels (article_generation.py:149); mapping keys are therefore idx+1. (3) Unused-reference trimming must happen BEFORE merging or dead entries enter the bibliography. (4) Final renumbering makes citation order == article order regardless of section completion order.
**Probe:** deterministic pins GREEN — storm_dataclass.py:192-196 (`len(...)+1` mint) and :128-132 (ascending-argsort top-k slice used by the retrieval feeding this merge) byte-verified this pass.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "storm", query: "merge new info references unified index url", limit: 10 });
```

## Verdict
Adopt the URL-keyed fold + post-hoc order-renumbering pair for parallel section generation with citations; adapt the key type (doc id instead of URL); omit the set-based snippet dedup if order matters downstream (it silently discards duplicates AND ordering). Caveat: no upstream tests; source-pinned.
