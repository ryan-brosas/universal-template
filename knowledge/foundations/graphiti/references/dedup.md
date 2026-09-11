<!-- capsule-v2 -->
# Fuzzy dedup — MinHash + LSH with entropy gating

**Source:** graphiti MIT `<branch>@<commit>`; Codebase Memory `graphiti`. **Question:** how does an entity-dedup system find near-duplicate names (Alice vs Alice Smith) without an LLM, using MinHash + LSH, and when does it defer to the LLM?

## Connected graph-selected seam
**Path/Symbol:** `graphiti_core/utils/maintenance/dedup_helpers.py` (296 lines): `_normalize_string_exact` (:39), `_normalize_name_for_fuzzy` (:45), `_name_entropy` (:52), `_has_high_entropy` (:79), `_shingles` (:88), `_minhash_signature` (:103), `_lsh_bands` (:117), `_jaccard_similarity` (:131), `DedupCandidateIndexes` (:150), `DedupResolutionState` (:161), `_resolve_with_similarity` (:220).
**Signature:** `_normalize_name_for_fuzzy` keeps alphanumerics+apostrophes for shingles; `_minhash_signature` builds a signature; `_lsh_bands` groups into bands for candidate detection; `_jaccard_similarity` scores.
**Data Shape:** 3-gram shingles; `_name_entropy` = Shannon entropy over characters (short/repetitive names → low entropy → defer to LLM); `_has_high_entropy` gates on `_MIN_NAME_LENGTH`/`_MIN_TOKEN_COUNT`/`_NAME_ENTROPY_THRESHOLD`.

### Decisive source
```ts
def _name_entropy(normalized_name):
    # Shannon entropy over characters; short or repetitive names yield low
    # entropy, signaling we should DEFER resolution to the LLM instead of
    # trusting fuzzy similarity
def _has_high_entropy(normalized_name):
    if len(normalized_name) < _MIN_NAME_LENGTH and token_count < _MIN_TOKEN_COUNT: return False
    return _name_entropy(normalized_name) >= _NAME_ENTROY_THRESHOLD
def _shingles(normalized_name): return {cleaned[i:i+3] for i in range(len(cleaned)-2)}  # 3-gram
```

**Flow:** normalize names (exact + fuzzy forms) → gate on entropy (low-entropy/short names defer to the LLM, never fuzzy-matched) → build 3-gram shingles → MinHash signature → LSH bands for candidate detection → Jaccard similarity scores candidates. `DedupCandidateIndexes`/`DedupResolutionState` track the candidate set and resolution.
**Invariant:** low-entropy or short names defer to the LLM (fuzzy similarity is only trusted on high-entropy names); MinHash+LSH makes candidate detection fast (no O(n²) scan); Jaccard scores the match.
**Probe:** `tests/` dedup tests (exact + fuzzy normalization; entropy gating defers short names; minhash+LSH finds candidates; jaccard threshold).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "graphiti", query: "dedup minhash LSH jaccard entropy shingles candidate resolve", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the MinHash+LSH fuzzy-dedup with entropy gating (defer low-entropy names to the LLM); adapt the shingle size, LSH bands, and similarity threshold to host.
