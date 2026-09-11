<!-- capsule-v2 -->
# Session-start recent-activity timeline — how do you show "what happened recently" without paying for a search?

**Source:** mem0 Apache-2.0 `main@7e096155714c`. **Question:** when a SessionStart hook wants a compact recent-activity banner, why does it FETCH a page instead of running a semantic search, and how does the global-scope flip work?

## Recent-memories fetch + timeline render (session_timeline.py)
**Path/Symbol:** `integrations/mem0-plugin/scripts/session_timeline.py:fetch_recent_memories` (lines 33–60) + `format_timeline` (63–86); wired by `scripts/on_session_start.sh` line ~174 under `SOURCE = startup` and `MEM0_COUNT != 0`.
**Signature:** `fetch_recent_memories(api_key: str, user_id: str, project_id: str) -> list[dict]`; `format_timeline(memories: list[dict]) -> str`.
**Data Shape:** `MAX_RECENT = 10`, `MAX_SUMMARIES = 3` (declared; the fetch is the binding cap), `FETCH_TIMEOUT = 5`; POST `{API_URL}/v3/memories/?page=1&page_size=10` with a FILTERS body (not a query): `{"AND": [{"user_id": uid}, {"app_id": pid}]}` normally, `{"OR": [{"user_id": "*"}]}` when `MEM0_GLOBAL_SEARCH=true`.

### Decisive source
```python
    if global_search:
        filters = {"OR": [{"user_id": "*"}]}
    else:
        filters = {"AND": [{"user_id": user_id}, {"app_id": project_id}]}
    body = json.dumps({"filters": filters}).encode()
    req = urllib.request.Request(
        f"{API_URL}/v3/memories/?page=1&page_size={MAX_RECENT}",
        data=body, ..., method="POST",
    )
```
The wrapper bounds it portably:
```bash
_TIMELINE=$(MEM0_CWD="$MEM0_CWD_RESOLVED" perl -e 'alarm 5; exec @ARGV' \
  python3 "$SCRIPT_DIR/session_timeline.py" 2>/dev/null || echo "")
```
**Flow:** SessionStart(startup) with memories present → banner tells the model to run 2 parallel searches → timeline injected below: fetch page 1 (recency order from the list endpoint, no query needed) → accept `{"results": [...]}` dict OR bare list → render `### Recent Activity` + `- {icon} [{cat}] ({age}) {text≤120} [mem0:{id8}]` lines via the shared `_formatting` funnel + a closing nudge to search for details. Any exception ⇒ `[]` ⇒ empty output ⇒ banner only.
**Invariant:** recency display uses the LIST endpoint (page sort), semantic recall uses the SEARCH endpoint — never conflate them; a search would rank by relevance to nothing. The global flip changes the FILTER SHAPE, not a flag: `user_id: "*"` inside an OR clause is the API's wildcard contract. `perl alarm 5` is the portable timeout because macOS lacks GNU `timeout`; the timeline is best-effort decoration and must never delay the banner.
**Probe:** no dedicated test file (honest gap); byte-exact grep probes executed this pass: `page_size={MAX_RECENT}` (1 hit), `{"OR": [{"user_id": "*"}]}` (1 hit), `perl -e 'alarm 5; exec @ARGV'` in on_session_start.sh (1 hit). Whole-file read both sides.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mem0", query: "session timeline recent memories fetch", limit: 10, fields: ["signature", "lines"] });
```
Recorded for graph-connected sessions; MCP not connected this pass (DEGRADED path, whole-file direct reads instead).

## Verdict
Adopt the fetch-vs-search split (recency = list page, recall = search) and the filter-shape scope flip for any memory banner. Adapt page size, the 5s alarm, and the timeline line format to your host. Omit the mem0 endpoint/auth shape. Coverage: both cited paths read whole; no dedicated tests (recorded gap, grep probes GREEN).
