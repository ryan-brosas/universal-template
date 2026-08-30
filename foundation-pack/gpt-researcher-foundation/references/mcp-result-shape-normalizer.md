<!-- capsule-v2 -->
# MCP result shape normalizer — how do arbitrary tool payloads become search-result dicts, and which sentinel URL is skipped at citation time?

**Source:** gpt-researcher Apache-2.0 `main@5d84d2f5553e70a2765a8ff3a0d2672d60437ce8`; Codebase Memory `gpt-researcher`. **Question:** What single dict shape must every MCP result reduce to, and where is LLM-self-analysis excluded from citations?

## _process_tool_result + _combine_mcp_and_web_context
**Path/Symbol:** `gpt_researcher/mcp/research.py:158-271` (`_process_tool_result`), `:137-149` (LLM-analysis mint); `gpt_researcher/skills/researcher.py:727-778` (`_combine_mcp_and_web_context` citation skip).
**Signature:** `def _process_tool_result(self, tool_name: str, result: Any) -> List[Dict[str, str]]`
**Data Shape:** Output contract `{title: str, href: str, body: str}`; href fallbacks mint deterministic pseudo-URLs `mcp://{tool_name}/{i}`.

### Decisive source
```python
# 1) MCP wrapper with structured_content/content — structured wins
if isinstance(result, dict) and ("structured_content" in result or "content" in result):
    structured = result.get("structured_content")
    if isinstance(structured, dict):
        items = structured.get("results")   # list → per-item rows
    ...
    if not search_results:
        content_field = result.get("content")  # MCP spec: [{type:"text", text:...}]
# ...else list / bare dict / scalar → str(item) body
...
llm_analysis = {"title": f"LLM Analysis: {query}",
                "href": "mcp://llm_analysis", "body": response.content}
```

**Flow:** four-shape ladder (MCP wrapper → list → dict → scalar), exception-safe with a stringify fallback row → combine step appends web context FIRST then MCP entries joined by `\n\n---\n\n`, each cited `*Source: title (url)*` EXCEPT when `url == "mcp://llm_analysis"` (title-only citation).
**Invariant:** the `mcp://` scheme is the marker distinguishing machine-minted provenance from real URLs — downstream URL dedupe and reference rendering treat them as opaque strings, so a porter inventing a different scheme breaks nothing TODAY but loses the citation-skip convention. The LLM's own analysis rides as a result so its synthesis reaches the writer.
**Probe:** battery P20a-c GREEN (`mcp://llm_analysis` ×1 in research.py, ×1 skip-check in researcher.py; `"structured_content" in result or "content" in result` ×1).
