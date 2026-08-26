<!-- capsule-v2 -->
# Two-phase citation renumbering — how do you remap citation numbers in text without collisions when the mapping is not injective?

**Source:** storm MIT `main@fb951af7`; Codebase Memory `storm`. **Question:** Why must `[old]→[new]` replacement run through a placeholder pass, and what breaks if you do it in one phase?

## Connected graph-selected seam
**Path/Symbol:** `knowledge_storm/utils.py:ArticleTextProcessing.update_citation_index` (:541-550); consumers `StormArticle.update_section` (storm_dataclass.py:286-288), `StormArticle.reorder_reference_index` (:374-412), `KnowledgeBase.update_from_conv_turn` (dataclass.py:802-822).
**Signature:** `update_citation_index(s: str, citation_map: Dict[int, int]) -> str`.
**Data Shape:** Map old citation number → unified number; applied to article/utterance text containing `[n]` markers.

### Decisive source
```python
for original_citation in citation_map:
    s = s.replace(f"[{original_citation}]", f"__PLACEHOLDER_{original_citation}__")
for original_citation, unify_citation in citation_map.items():
    s = s.replace(f"__PLACEHOLDER_{original_citation}__", f"[{unify_citation}]")
```

**Flow:** Pass 1 hides every mapped old marker behind a token that cannot collide with any `[k]`; pass 2 rewrites placeholders to final numbers. Because pass-2 outputs are indistinguishable from unmapped text, chained application is safe.
**Invariant:** (1) One-phase replace is WRONG whenever some new value equals a later old key (e.g. `{1→2}` on `"[1]"` would double-apply) — the placeholder moat is the whole trick. (2) The map must be built from per-section citation usage BEFORE merging references (`index_to_keep = [i - 1 for i in used_refs]`, storm_dataclass.py:267-285). (3) The twin function in Co-STORM (`KnowledgeBase.update_from_conv_turn`) does NOT use this helper — it hand-rolls `[_{new}_]` intermediate tokens and then leaves two latent no-op statements `.replace("[-1]", "")` whose results are discarded (:818, :822), so stale `[-1]` markers survive.
**Probe:** executed lifted probe GREEN — collision case `update_citation_index("[1]+[2]", {1:2, 2:1}) == "[2]+[1]"` and prefix-safety `"[1] and [12]" | {1:5} → "[5] and [12]"` (T03 in scratch-storm-pass1/probe_gate5.py); latent no-op pinned byte-exact at dataclass.py:817-822.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "storm", query: "update_citation_index PLACEHOLDER citation map", limit: 10 });
```

## Verdict
Adopt the two-phase placeholder rewrite verbatim for ANY citation/index renumbering; adapt token format; omit nothing — the one-phase shortcut is the classic corruption bug. Note `parse_citation_indices` extracts SINGLE-number `[d+]` matches only, so grouped `[2, 3]` are invisible to it (utils.py:363-364; probe T08 GREEN). Caveat: no upstream tests; probes executed against lifted source.
