<!-- capsule-v2 -->
# MCP server agent fallback — direct CDP tool surface with one autonomous-agent escape hatch

**Source:** browser-use MIT `main@85ddbfedf609`; Codebase Memory `browser-use`. **Question:** when you expose a browser to an LLM over MCP, which operations stay deterministic CDP tools and how does the one non-deterministic operation (full agent run) degrade gracefully?

## Connected graph-selected seam
**Path/Symbol:** `browser_use/mcp/server.py` (1290 lines): `BrowserUseServer._execute_tool` (:493-576), `_retry_with_browser_use_agent` (:644-746), `_init_browser_session` (:578+, lazy), `_setup_handlers` (:212-491), `run`/`main` (:1238-1290).
**Signature:** dispatch by name: the reserved tool `retry_with_browser_use_agent`, session-management tools (`browser_list_sessions`, `browser_close_session`, `browser_close_all`), then prefix-gated `browser_*` direct tools (navigate/click/type/get_state/get_html/screenshot/extract_content/scroll/go_back/close/list_tabs/switch_tab/close_tab) that lazily create the shared session.
**Data Shape:** plain tools return `str`; image-bearing tools (`browser_get_state`, `browser_screenshot`) return MCP content lists `[TextContent(json state/meta), ImageContent(png base64)]`. The agent fallback returns ONE multi-section report string.

### Decisive source
```python
# EMPTY-LIST GUARD: only a NON-empty client list may override the admin allowlist,
# because SecurityWatchdog interprets allowed_domains=[] as "no restrictions".
if allowed_domains:
    profile_config['allowed_domains'] = allowed_domains

# provider ladder for the fallback agent (tool model arg > config default)
if model_provider and model_provider.lower() == 'bedrock':
    llm_model = llm_config.get('model') or os.getenv('MODEL') or 'us.anthropic.claude-sonnet-4-6'
    aws_region = llm_config.get('region') or os.getenv('REGION') or 'us-east-1'
    llm = ChatAWSBedrock(model=llm_model, aws_region=aws_region, aws_sso_auth=llm_config.get('aws_sso_auth', False))
else:
    api_key = llm_config.get('api_key') or os.getenv('OPENAI_API_KEY')
    if not api_key:
        return 'Error: OPENAI_API_KEY not set in config or environment'   # STRING result, never an exception

try:
    history = await agent.run(max_steps=max_steps)
    results.append(f'Task completed in {len(history.history)} steps')
    results.append(f'Success: {history.is_successful()}')
    if final_result := history.final_result(): results.append(f'\nFinal result:\n{final_result}')
    if errors := history.errors(): results.append(f'\nErrors encountered:\n{json.dumps(errors, indent=2)}')
    valid_urls = [str(u) for u in history.urls() if u is not None]
    return '\n'.join(results)
except Exception as e:
    return f'Agent task failed: {str(e)}'      # agent failure degrades to text, tool contract intact
finally:
    await agent.close()                        # teardown ALWAYS runs, even on client cancel
```

**Flow:** MCP client calls a tool -> `_execute_tool` routes: agent tool first; session tools need no session; every `browser_*` tool lazily runs `_init_browser_session` which merges profile defaults < `get_default_profile(config)` < tool kwargs into one `BrowserProfile`, starts `BrowserSession`, tracks it for close-all, and builds `Tools()` + `FileSystem(~/.browser-use-mcp)` -> direct handlers call session APIs and serialize state/screenshot to MCP content parts.
**Invariant:** the MCP tool contract never throws for agent failures — every failure path returns a human-readable string so the calling LLM can read it; missing API keys return error strings instead of raising; the fallback agent gets its own profile/session (never reuses the interactive one); `agent.close()` is unconditional in `finally`; unknown tool names fall through to `Unknown tool: <name>`.
**Probe:** from repo root, instantiate nothing network-bound: assert dispatch ordering by reading source ranges above via graph snippet retrieval, and verify the empty-list guard with a tiny in-process check of the merge predicate (executed this pass; output in verification.md).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "browser-use", query: "BrowserUseServer retry_with_browser_use_agent execute tool", file_pattern: "browser_use/mcp/server.py", limit: 12 });
```

## Verdict
Adopt the three-ring tool surface: deterministic primitives, session lifecycle verbs, and exactly ONE agentic fallback whose failures degrade to strings. Copy the empty-list guard verbatim wherever an empty collection could silently widen permissions. Adapt provider selection to your gateway; keep "config errors are tool RESULTS, not exceptions" — it preserves the MCP contract under partial misconfiguration.
