<!-- capsule-v2 -->
# Google-search-as-tool contract — how does an agent search the web in ONE action instead of driving a search page?

**Source:** TheAgenticBrowser (TheAgentic Community License 1.0) `main@71daa28`; Codebase Memory `mnt-hdd-utopia-inspo-TheAgenticBrowser`. **Question:** What should an API-backed search tool return (and swallow) so the LLM can chain results into open_url navigation?

## Custom Search JSON API with num≤10 clamp and error-string returns
**Path/Symbol:** `core/skills/google_search.py`:`google_search` (`:7-56`); BA wrapper `core/agents/browser_agent.py:242-247`; prompt contract `core/agents/browser_agent.py:53-58`.
**Signature:** `async def google_search(query: str, num: int = 10) -> str`.
**Data Shape:** Formatted plain text: header line with query, total-results count, search time; then per-result `Title:/URL:/Snippet:` blocks separated by blank lines. Requires `GOOGLE_API_KEY` + `GOOGLE_CX` env pair.

### Decisive source
```python
params = {"key": api_key, "cx": cx, "q": query, "num": min(num, 10)}   # API ceiling
response = requests.get(base_url, params=params)
response.raise_for_status()
...
except requests.RequestException as e:
    return f"Error performing Google search: {str(e)}"
except ValueError as e:
    return str(e)
except Exception as e:
    return f"An unexpected error occurred: {str(e)}"
```
The system prompt pairs it with a navigation rule: keep results in mind for future hops ("To navigate to a website using this tool you need to use the open_url_tool with a URL from google_search"), and the planner is told the trade-off explicitly — API search = one fast action; normal engine search = more detailed but multi-action.
**Flow:** tool_plain wrapper → env check → blocking requests GET (inside async! see invariant) → raise_for_status → flatten items[] → formatted string.
**Invariant:** ALL failures return strings rather than raising — a failed search must reach the critique loop as evidence, never kill the browser agent mid-step. The `num` clamp mirrors Google's hard max of 10; larger values would 400. Note the porting trap: this uses BLOCKING `requests` inside an async def — acceptable here because search happens once per task, but a hot loop should switch to httpx/asynchttp.
**Probe:** No tests (coverage caveat). Graph pins: `google_search_tool` listed as tool #1 in the BA system prompt's `<tools>` section with its own `<parameters>` block (:94-102); planner prompt rule references it as "google search api" (:36).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-TheAgenticBrowser", query: "google search custom api num", limit: 10, fields: ["name", "file"] });
```

## Verdict
Adopt error-as-data search returning structured plain text the model can parse. Adapt provider (SerpAPI/Bing/Brave equivalents drop in behind the same signature). Omit the blocking-client pattern under concurrency.
