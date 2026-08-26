<!-- capsule-v2 -->
# find_tools error-to-agent contract — when the tool SHORTLISTER itself fails, why must it return a retryable error STRING instead of raising?

**Source:** cuga-agent Apache-2.0 `main@5de53ade77c36166da6ace906af488b2b445454f`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** How should an agent-facing meta-tool (that uses another LLM call internally) behave when its internal LLM parse fails?

## Catch-and-stringify inside the StructuredTool, never raise into the graph
**Path/Symbol:** `src/cuga/backend/cuga_graph/nodes/cuga_lite/helpers/find_tools.py:63-146` (`create_find_tools_tool`, inner `find_tools_func`).
**Signature:** `async def create_find_tools_tool(all_tools, all_apps, app_to_tools_map=None, llm=None, initial_user_message=None) -> StructuredTool`; inner `find_tools_func(query: str, app_name: str)`.
**Data Shape:** Query composition: `"Query: {q}\nTask context (initial user message): {init}"` — the shortlister sees the original task, not just the sub-query. Unknown `app_name` in a provided map ⇒ warning + empty list (not all-tools).

### Decisive source
```python
# find_tools.py:117-133
except OutputParserException as e:
    logger.bind(query_len=len(shortlister_query),
                error_type=type(e).__name__,
                ).opt(exception=True).warning(
        "Tool shortlisting failed due to parser error; returning error to agent")
    return (
        f"Tool shortlisting failed due to malformed response: {e}. "
        "Please retry with a different query."
    )
except Exception as e:
    ... return f"Tool shortlisting failed due to an internal error: {e}. ..."
```
The failure mode this prevents: if `find_tools` raised, LangGraph would treat it as the AGENT's tool failing — the agent loop's error handling kicks in for something that is really an internal retrieval-service outage. Returning a structured natural-language error keeps the failure INSIDE the conversation: the agent reads "retry with a different query" and adapts, exactly like any other tool observation. The nested LLM call runs under `nested_langgraph_invoke_config()` so tracing attributes the span to the right node rather than the outer run.

**Flow:** agent calls `find_tools(query, app_name)` → filter tools by app map (missing app ⇒ warn + empty) → compose query with initial user message → PromptUtils.find_tools LLM shortlist → parse error or internal error ⇒ log-with-bound-context and return retry-me string; success ⇒ matching tools.
**Invariant:** A meta-tool's INTERNAL failures are observations, not exceptions; every error return explicitly invites a retry. Diagnostics bind structured fields (`query_len`, `error_type`) instead of baking them into message text.

**Probe:** No dedicated unit test for find_tools in tests/unit — coverage caveat: exercised via e2e CRM tests (`crm_contacts_email_test_find_tools.py`); read source when porting.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "create_find_tools_tool shortlister OutputParserException", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt catch-and-stringify with explicit retry invitation for any tool wrapping its own model calls, plus bound-field diagnostics. Adapt wording to your agent's conventions. Omit task-context composition only if your agents never issue under-specified queries.
