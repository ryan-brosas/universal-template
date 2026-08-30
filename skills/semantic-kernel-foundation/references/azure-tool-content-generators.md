<!-- capsule-v2 -->
# Azure per-tool content generators — RunStep tool calls folded into SK content items

**Source:** Microsoft semantic-kernel MIT `main@b39d95a34435f4c1d55dd00c86120ce118d847e1`; Codebase Memory `semantic-kernel`. **Question:** How does each Azure AI tool type map to FunctionCallContent/FunctionResultContent items, and what is THREAD_MESSAGE_ID for?

## generate_*_content dispatch family
**Path/Symbol:** `python/semantic_kernel/agents/azure_ai/agent_content_generation.py:generate_bing_grounding_content` (lines 311–337), `generate_azure_ai_search_content` (340–374), `generate_deep_research_content` (396–443), `_extract_unique_urls` (446–455), `generate_mcp_content` (941–961), `generate_mcp_call_content` (964–987), `generate_streaming_message_content` (161–203), `THREAD_MESSAGE_ID` (line 69), `generate_message_content` metadata (106–127).
**Signature:** `def generate_bing_grounding_content(agent_name: str, bing_tool_call: "RunStepBingGroundingToolCall | RunStepBingCustomSearchToolCall") -> ChatMessageContent`; `def generate_azure_ai_search_content(agent_name: str, azure_ai_search_tool_call: "RunStepAzureAISearchToolCall") -> ChatMessageContent | None`; `def generate_deep_research_content(agent_name: str, deep_research_tool_call: "RunStepDeepResearchToolCall") -> ChatMessageContent`.
**Data Shape:** Input: Azure SDK `RunStep*ToolCall` objects. Output: `ChatMessageContent(role=ASSISTANT)` (or TOOL for function results) whose `items` mix `FunctionCallContent` / `FunctionResultContent` / `TextContent`. Streaming twins take `RunStepDeltaToolCallObject` and return `StreamingChatMessageContent | None` (None = nothing to yield).

### Decisive source
```python
# Bing grounding: CALL-ONLY — the whole tool-details dict becomes the arguments
message_content.items.append(FunctionCallContent(
    id=bing_tool_call.id, name=bing_tool_call.type, function_name=bing_tool_call.type,
    arguments=tool_details))          # bing_grounding | bing_custom_search dict

# Azure AI Search: CALL+RESULT pair, each carrying the raw tool call as inner_content
arguments = azure_ai_search_tool_call.azure_ai_search.get("input")
if arguments:
    items.append(FunctionCallContent(..., inner_content=azure_ai_search_tool_call))
result = azure_ai_search_tool_call.azure_ai_search.get("output")
if result:
    items.append(FunctionResultContent(..., result=result, inner_content=azure_ai_search_tool_call))
return ChatMessageContent(role=AuthorRole.ASSISTANT, name=agent_name, items=items) if items else None

# Deep Research: call+result plus a markdown citations section from unique URLs
urls = _extract_unique_urls(str(output_text))
if urls:
    citations_lines = ["## Citations"] + [f"{i + 1}. [{u}]({u})" for i, u in enumerate(urls)]
    items.append(TextContent(text="\n\n" + "\n".join(citations_lines)))

def _extract_unique_urls(text: str) -> list[str]:
    seen: set[str] = set(); ordered: list[str] = []
    for match in _URL_PATTERN.finditer(text or ""):
        url = match.group(0)
        if url not in seen:
            seen.add(url); ordered.append(url)
    return ordered

# MCP: result content keeps the raw SDK call as inner_content; call content carries server_label
mcp_result = FunctionResultContent(function_name=mcp_tool_call.name, id=mcp_tool_call.id,
                                   result=mcp_tool_call.output)
return ChatMessageContent(role=AuthorRole.ASSISTANT, name=agent_name, items=[mcp_result],
                          inner_content=mcp_tool_call)

# streaming delta stamping — thread_msg_id travels in metadata
metadata: dict[str, Any] | None = None
if thread_msg_id:
    metadata = {THREAD_MESSAGE_ID: thread_msg_id}
```

**Flow:** `agent_thread_actions` walks completed run steps and dispatches each `RunStep*ToolCall` to its
generator. The mapping asymmetries are the porting surface: Bing grounding/custom search emit ONE
FunctionCallContent whose arguments are the ENTIRE tool-details dict (requesturl, response_metadata, query,
custom_config_id, search_results) — no result item; Azure AI Search and Deep Research emit call+result pairs
and return None when BOTH halves are empty (caller skips the yield); Deep Research additionally appends a
`## Citations` markdown TextContent built from order-preserved unique URLs (regex
`https?://[^\s\]\)]+`, case-insensitive); OpenAPI and file search emit call+result with arguments/output
pulled from the function dict; MCP result content preserves the raw SDK call as `inner_content` while MCP
call content carries `server_label` on each FunctionCallContent. Streaming twins mirror each generator but
return None when no items were produced. `generate_message_content` metadata carries BOTH `message_id` and
`thread_message_id` (same value — the duplicate key avoids breaking the legacy `message_id` consumers);
streaming deltas carry `THREAD_MESSAGE_ID` metadata when the caller passes `thread_msg_id`, which is how
`agent_thread_actions._process_stream_events` correlates a delta to its thread message.
**Invariant:** Every generator is a pure fold — no runtime state, no I/O. Streaming twins must return None
(not an empty message) when nothing matched, so the caller can skip the yield. URL extraction preserves
first-appearance order and dedupes. Function results for the function tool path use role TOOL; all
server-side tool generators use role ASSISTANT.
**Probe:** `python/tests/unit/agents/azure_ai_agent/test_agent_content_generation.py::test_generate_bing_grounding_content` (arguments carry requesturl + response_metadata verbatim), `test_generate_bing_custom_search_content`, `test_generate_streaming_function_content_with_function` (arguments stringified), `test_generate_streaming_message_content_text_only_no_annotations` (`metadata[THREAD_MESSAGE_ID] == "thread_1"`), `test_generate_function_result_content` (role TOOL, result "result_data"), `test_generate_code_interpreter_content` (`metadata["code"] is True`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "semantic-kernel", query: "generate_deep_research_content generate_mcp_content THREAD_MESSAGE_ID _extract_unique_urls RunStepBingGroundingToolCall azure_ai_search", limit: 10, fields: ["signature", "name", "file"] });
```
(Not executable this pass — MCP surface absent; query kept byte-for-byte for the next connected pass.)

## Verdict
Adopt: the per-tool pure-fold generator pattern with call-only vs call+result asymmetries, inner_content
preservation of raw SDK objects, server_label on MCP calls, and the THREAD_MESSAGE_ID metadata correlation
key. Adapt the Azure SDK types to your provider's tool-call shapes. Omit the Deep Research citations
section if your surface has no research tool.
