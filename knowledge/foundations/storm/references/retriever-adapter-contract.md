<!-- capsule-v2 -->
# Retriever adapter contract — what must every search-engine wrapper return, and which parameters are traps?

**Source:** storm MIT `main@fb951af7`; Codebase Memory `storm`. **Question:** What is the uniform `dspy.Retrieve` subclass contract across You/Bing/Serper/Brave/SearXNG/DDG/Tavily/Google/Azure/Vector backends?

## Connected graph-selected seam
**Path/Symbol:** `knowledge_storm/rm.py` — e.g. `SerperRM.forward` (:490-567), `AzureAISearch.forward` (:1190-1238), `VectorRM.forward` (:306-337).
**Signature:** `forward(query_or_queries: Union[str, List[str]], exclude_urls: List[str] = []) -> List[Dict]` where each dict has EXACTLY keys `description`, `snippets` (List[str]), `title`, `url`.
**Data Shape:** Query-count accounting via `self.usage += len(queries)` + `get_usage_and_reset() -> {"<RMName>": int}`; optional `is_valid_source(url) -> bool` filter; API-key resolution ladder param → env var → RuntimeError.

### Decisive source
```python
# TRAP 1 — exclude_urls is a dummy on several engines:
def forward(self, query_or_queries, exclude_urls):   # VectorRM / SerperRM / TavilySearchRM / AzureAISearch
    """... exclude_urls (List[str]): Dummy parameter to match the interface. Does not have any effect."""
# TRAP 2 — AzureAISearch hardcodes top=1 regardless of self.k:
results = client.search(search_text=query, top=1)
# TRAP 3 — Serper mutates SHARED self.query_params per query and skips the literal "Queries:" string:
if query == "Queries:": continue
query_params["q"] = query; query_params["type"] = "search"
```

**Flow:** All engines normalize str→list, count usage, then either (a) return SERP snippets directly (You/Brave/serper organic), (b) fetch SERP urls then scrape full pages via shared `WebPageHelper.urls_to_snippets` for richer snippets (Bing/Google/DDG/Tavily-raw), or (c) embed-query over a vector collection (VectorRM). Results funnel into the same four-key dict shape that `Retriever.retrieve` converts to `Information.from_dict`.
**Invariant:** (1) The four-key dict IS the portability boundary — add fields under `meta`, never as new top-level keys. (2) `exclude_urls` semantics differ per engine: honored on You/Bing/Brave/SearXNG/DDG/Tavily/Google, silently ignored on Serper/VectorRM/Azure — callers relying on it with those engines leak excluded sources. (3) Per-query exceptions are logged and SKIPPED (loop continues), never raised — one bad query never kills a turn. (4) WebPageHelper scrapes with `httpx verify=False`, 4s timeout, trafilatura extraction, ≥min_char_count gate, RecursiveCharacterTextSplitter with CJK-aware separators.
**Probe:** deterministic pins GREEN — rm.py AzureAISearch `top=1` (:1225) and two "Dummy parameter" docstrings byte-verified this pass.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "storm", query: "SerperRM forward organic snippet", limit: 10 });
```

## Verdict
Adopt the dict-shape + usage-ledger + skip-on-error contract for swappable search backends; adapt per-engine params; NEVER assume exclude_urls works engine-uniformly. Related seam: `Retriever.retrieve` (interface.py:288-319) fans queries through a ThreadPoolExecutor and strips citations from SOURCE snippets before storage ("we do not consider multi-hop citations"). Caveat: no upstream tests; source-pinned.
