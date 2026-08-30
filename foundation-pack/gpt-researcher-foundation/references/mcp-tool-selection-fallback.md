<!-- capsule-v2 -->
# MCP tool selection fallback — how are a server's tools narrowed to three, and what happens when the LLM selector fails?

**Source:** gpt-researcher Apache-2.0 `main@5d84d2f5553e70a2765a8ff3a0d2672d60437ce8`; Codebase Memory `gpt-researcher`. **Question:** What is the degrade-not-crash chain for choosing which MCP tools a research query may call?

## MCPToolSelector.select_relevant_tools
**Path/Symbol:** `gpt_researcher/mcp/tool_selector.py:35-127` (LLM arm), `:163-204` (`_fallback_tool_selection`); client lifecycle `mcp/client.py:40-103` (`convert_configs_to_langchain_format` transport auto-detect ws/wss→websocket, http(s)→streamable_http, else stdio with args/env; token + headers passthrough).
**Signature:** `async def select_relevant_tools(self, query: str, all_tools: List, max_tools: int = 3) -> List`
**Data Shape:** LLM returns `{selected_tools:[{index,name,reason,relevance_score}], selection_reasoning}`; selection by INDEX into the original list.

### Decisive source
```python
research_patterns = [
    'search', 'get', 'read', 'fetch', 'find', 'list', 'query',
    'lookup', 'retrieve', 'browse', 'view', 'show', 'describe'
]
score = 0
for pattern in research_patterns:
    if pattern in tool_name:        # name hit worth 3
        score += 3
    if pattern in tool_description: # description hit worth 1
        score += 1
```

**Flow:** ≤3 tools needed → no LLM call at all → else strategic LLM at temperature 0.0 → strict JSON parse, then greedy `{.*}` extraction, then pattern fallback on ANY failure (empty response, JSONDecodeError, zero valid indices, exception) → execution binds selected tools via `llm.bind_tools` and runs each tool_call (`mcp/research.py:85-135`, per-tool try/continue).
**Invariant:** every failure path returns tools (possibly pattern-scored), never raises — an MCP outage degrades research quality, it must not abort the run. Index-based selection requires the tool list ORDER to stay stable between selection and binding.
**Probe:** `tests/test_mcp_client_config.py` pins headers forwarding for streamable_http/websocket and none-when-absent; battery P19a GREEN (pattern list line ×1).
