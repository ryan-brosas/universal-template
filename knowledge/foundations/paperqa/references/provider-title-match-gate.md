<!-- capsule-v2 -->
# Crossref title-match gate — how do you reject a wrong paper when the API's relevance score is untrustworthy?

**Source:** paper-qa (Apache-2.0) `main@57e89f72`; Codebase Memory `ext-paper-qa`. **Question:** When searching Crossref/S2/OpenAlex by TITLE (no DOI), what acceptance test prevents silently citing a different paper that merely ranks first?

## Connected graph-selected seam
**Path/Symbol:** `src/paperqa/clients/crossref.py:get_doc_details_from_crossref` (:253-349); twins `semantic_scholar.py:s2_title_search` (:238-294), `openalex.py:get_doc_details_from_openalex` (:162-171).
**Signature:** `title_similarity_threshold: float = 0.75` threaded from `TitleAuthorQuery` (validated ∈ [0,1], sorted-fields canonicalized for caching).
**Data Shape:** Similarity metric = word-set Jaccard (`utils.strings_similarity`: |intersection|/|union| of lowercased word sets). Non-JSON responses and HTTP failures both raise `DOINotFoundError` so the ladder falls through to the next provider.

### Decisive source
```python
if doi is not None and title is not None:
    title = None  # Prefer DOI over title
...
# since score is not consistent between queries, we need to rely on our own criteria
if (doi is None and title
    and strings_similarity(message["title"][0], title) < title_similarity_threshold):
    raise DOINotFoundError(f"Crossref results did not match for title {title!r}.")
if doi is not None and message["DOI"] != doi:
    raise DOINotFoundError(f"DOI ({inputs_msg}) not found in Crossref")
```
S2 twin adds an AUTHOR cross-check: with authors supplied, accept only if title similarity is EXACTLY 1.0 OR `s2_authors_match` (initials-stripped bidirectional substring over words >2 chars) passes; without authors, ONLY exact title similarity 1.0 is accepted (`HIGH_TITLE_SIMILARITY_THRESHOLD = 1.0`).

**Flow:** DOI query path skips similarity entirely but demands exact DOI echo-back. ArXiv preprints synthesize `10.48550/arXiv.<id>` BEFORE any DOI check (S2 externalIds priority). Empty S2 result lists surface as ValueError from max() → converted to DOINotFoundError.
**Invariant:** The provider's own ranking score is NEVER trusted across queries — only local Jaccard + exact DOI echo; every rejection raises the same DOINotFoundError type so the client ladder treats "wrong paper" identically to "no paper".
**Probe:** `tests/test_clients.py::test_author_matching` (:535), `::test_s2_title_search_edge_cases` (:392), `::test_bad_titles` (:351), `::test_bad_dois` (:415).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-paper-qa", query: "strings_similarity title_similarity_threshold DOINotFoundError", limit: 10 });
// SIMILAR_TO edges link the three provider twins implementing this gate
```

## Verdict
Adopt local-Jaccard-over-rank + exact-DOI-echo as THE acceptance contract; adapt threshold per corpus (0.75 default); omit the S2 initials heuristic if your provider returns clean author lists. Coverage caveat: provider tests require network fixtures; logic pinned by cited tests + source read.
