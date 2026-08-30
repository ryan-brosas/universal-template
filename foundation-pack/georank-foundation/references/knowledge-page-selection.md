<!-- capsule-v2 -->
# Knowledge-page selection — which links earn a crawl when the LLM is down?

**Source:** GEOrank (aeo-georank) Apache-2.0 `main@424a0cf92b37ad63c94ae9dc6f39745189ab7c94`; Codebase Memory `ext-aeo-georank`. **Question:** How do you rank a homepage's nav links into the 2–3 "about this company" pages worth crawling, deterministically, with an AI path that degrades to heuristics?

## Candidate filter → weighted keyword rank → role classify
**Path/Symbol:** `backend/app/services/company_ingest.py`: `build_candidate_links` :176–212, `_POSITIVE_KEYWORDS` :33–50 / `_NEGATIVE_KEYWORDS` :52–68 (weighted dicts), `_ROLE_PATTERNS` :70–74, `_classify_role` :214–220, `fallback_select_company_pages` :222–273; AI twin `ai_client.select_company_pages`; orchestrator `_plan_company_pages` in `tasks/crawl.py` :306–333.
**Signature:** `build_candidate_links(base_url: str, anchors: Iterable[dict], *, limit: int = 12) -> list[dict]`; `fallback_select_company_pages(base_url, homepage_title, candidate_links, *, limit=3) -> list[dict]`.
**Data Shape:** Anchor in: `{url, title}`; candidate out: `{url(normalized), title(≤80), path}`; selected page out: `{url, title, role: homepage|about|team|product|supporting, reason}`.

### Decisive source
```python
if href in seen or href == normalized_base: continue
if not _same_domain(normalized_base, href): continue
if parsed.path.lower().endswith(_ASSET_EXTENSIONS): continue   # .jpg .pdf .css ...
if parsed.query or parsed.fragment: continue
if _path_depth(parsed.path) > 1: continue                      # top-nav only
```
```python
score -= _path_depth(candidate.get("path") or "/") * 4.0       # shallow nav wins
# about:+90 team:+80 product:+56 | login/registration:-120 privacy:-70 careers:-20 blog:-18
```

**Flow:** filter anchors to same-origin asset-free query-free depth-≤1 links (dedup, cap 12) → try LLM selection (`ai_client.select_company_pages`) with heuristic fallback on ANY exception → ALWAYS force-insert the normalized homepage at position 0 with role=homepage → cap at 3 pages. Crawl loop marks failed sub-pages `status:"failed"` with truncated reason but keeps the record — partial evidence beats none.
**Invariant:** The homepage can never be dropped or outranked; selection output shape is identical for the AI and fallback paths so downstream code never branches on which ran; `_classify_role` falls back to "supporting" and the reason strings are per-role templates.
**Probe:** `backend/tests/test_company_profile.py::fallback-selection*` assertions on keyword weights + depth penalty ordering.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-aeo-georank", query: "fallback_select_company_pages", limit: 5 });
// verified line-exact: company_ingest.py :222–273
```

## Verdict
Adopt the weighted-keyword page selector for any site-understanding crawler; adapt keyword dictionaries per language/market (these are zh-market tuned); omit LLM selection if budget-bound — the fallback alone is shippable.
