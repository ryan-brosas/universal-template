<!-- capsule-v2 -->
# Report-source dispatch & curator fail-open — which data plane runs for each report_source, and what happens when LLM curation fails?

**Source:** gpt-researcher Apache-2.0 `main@5d84d2f5553e70a2765a8ff3a0d2672d60437ce8`; Codebase Memory `gpt-researcher`. **Question:** How does `report_source` select its research data plane, and why must a curation failure degrade to uncurated passthrough instead of an error?

## ResearchConductor.conduct_resource dispatch ladder + SourceCurator passthrough
**Path/Symbol:** `gpt_researcher/skills/researcher.py:145-205` (dispatch ladder), `:209-225` (curator gate + normalization); `gpt_researcher/skills/curator.py:33-96` (`curate_sources`).
**Signature:** `async def conduct_research(self)` (reads `self.researcher.report_source/source_urls/complement_source_urls`); `async def curate_sources(self, source_data: List, max_results: int = 10) -> List`.
**Data Shape:** `research_data` may be str (web paths join later), list (vectorstore gather), or curated dict list; `researcher.context` ends as str in every branch after normalization.

### Decisive source
```python
# researcher.py:155-158 — explicit complement arm:
if self.researcher.complement_source_urls:
    additional_research = await self._get_context_by_web_search(
        self.researcher.query, [], self.researcher.query_domains)
    research_data += ' '.join(additional_research)
# researcher.py:215-223 — curator output MUST be flattened back to str:
if isinstance(curated, list):
    self.researcher.context = "\n\n".join(
        "Title: {title}\nContent: {content}\nSource: {source}".format(...)
        if isinstance(s, dict) else str(s) for s in curated)
```
```python
# curator.py:87-96 — strict json.loads inside try; ANY failure returns inputs unchanged:
except Exception as e:
    print(f"Error in curate_sources from LLM response: {response}")
    ...
    return source_data
```

**Flow:** dispatch order is `source_urls` (scrape-only, optional web complement) → `Web` → `Local` (DocumentLoader + optional vector_store.load) → `Hybrid` (Online/Local docs pass and web pass run CONCURRENTLY via `asyncio.gather`, joined by `prompt_family.join_local_web_documents`) → `Azure` (container/connection string read from os.environ at call time) → `LangChainDocuments` → `LangChainVectorStore` → then optional `cfg.curate_sources` gate.
**Invariant:** curation is strictly opt-in, best-effort, and shape-restoring: a malformed LLM response never fails research (fail-open returns original sources), and whatever comes back is normalized to the string contract downstream code assumes (`"\n".join`, `.split()`, `len()`); the Azure arm is the ONLY branch reading env vars directly.
**Probe:** runner BLOCKED this lane (no aiofiles/deps; read-only checkout). Deterministic anchors verified byte-exact against the pin: `complement_source_urls:` at researcher.py:155, `return source_data` at curator.py:96, `"Title: {title}"` format literal at researcher.py:217; direct tests absent upstream for both arms (recorded caveat).
**Coverage:** check_index_coverage `no_recorded_issue`/`metadata_match` for skills/researcher.py + skills/curator.py @ gen 2026-08-26T01:42:19Z.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "gpt-researcher", query: "conduct_research report_source curate_sources", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the ladder order, the concurrent hybrid gather, and fail-open curation with string normalization — they encode "research must produce context even when ranking fails". Adapt plane loaders to your storage hosts; replace the env-var Azure credentials read. Omit the print-based logging and the frontend MCP preset coupling.
