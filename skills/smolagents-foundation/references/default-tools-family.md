<!-- capsule-v2 -->
# Base tools & search-tool family — which ready-made tools exist, and what contracts do the web-search twins share?

**Source:** smolagents Apache-2.0 `main@30bb1161`; Codebase Memory `ext-smolagents`. **Question:** What is in `default_tools.py` (the TOOL_MAPPING set agents may auto-add), and what invariant do the four `web_search` implementations share that a porter must keep?

## Tool inventory + markdown result contract
**Path/Symbol:** `src/smolagents/default_tools.py` — PythonInterpreterTool (:39-80), FinalAnswerTool (:83-90), UserInputTool (:93-101), DuckDuckGoSearchTool (:104-159), GoogleSearchTool (:162-246), ApiWebSearchTool (:249-339), WebSearchTool (:342-488), VisitWebpageTool (:491-544), WikipediaSearchTool (:547-643), SpeechToTextTool (:646-675), TOOL_MAPPING (:678-685).
**Signature:** All searches share `name="web_search"`, `inputs={"query": string}`, `output_type="string"`; per-instance rate limiting via `_enforce_rate_limit()` (`_min_interval = 1.0/rate_limit`, sleep-to-interval, stamp AFTER request).
**Data Shape:** Result text always opens `"## Search Results\n\n"` then `[title](url)\ndescription` blocks joined by blank lines — the LLM-facing format IS the API.

### Decisive source
```python
# :140-146 — DuckDuckGo twin; every sibling mirrors this shape:
def forward(self, query: str) -> str:
    self._enforce_rate_limit()
    results = self.ddgs.text(query, max_results=self.max_results)
    if len(results) == 0:
        raise Exception("No results found! Try a less restrictive/shorter query.")
    postprocessed_results = [f"[{result['title']}]({result['href']})\n{result['body']}" for result in results]
    return "## Search Results\n\n" + "\n\n".join(postprocessed_results)
```

**Flow:** TOOL_MAPPING exposes exactly {python_interpreter, web_search(DuckDuckGo), visit_webpage} for `add_base_tools=True`; note `_setup_tools` EXCLUDES python_interpreter for CodeAgents (they get the sandbox instead) — agents.py:399. The four web_search twins split along auth: DDGS lib / SerpAPI-Serper key-from-env with year filter via tbs param / Brave API with headers+params injection / engine-dispatched scraper trio (DDG lite HTML parser, Bing RSS XML, Exa API) — all normalizing to the identical markdown contract so prompts never change per backend. VisitWebpageTool converts HTML→markdown, collapses 3+ newlines, truncates at 40k chars, and returns error TEXT instead of raising on fetch failures.
**Invariant:** Same-name tools are interchangeable from the agent's perspective; breaking the `"## Search Results"` preamble or the empty-result exception ("try a less restrictive/shorter query") breaks prompt-level behavior the model has implicitly learned. python_interpreter exclusion for CodeAgent prevents two competing execution surfaces.
**Probe:** `tests/test_search.py::TestDuckDuckGoSearchTool.setup_method` (+ mock-based forward tests), `tests/test_default_tools.py` (visit_webpage formatting). Live: instantiate each search tool class and assert name=="web_search", output_type=="string".

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-smolagents", query: "DuckDuckGoSearchTool WebSearchTool TOOL_MAPPING web_search", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt one normalized result format across interchangeable backend twins. Adapt backends/rate limits to your keys. Omit the CodeAgent python_interpreter exclusion at the cost of ambiguous execution semantics.
