<!-- capsule-v2 -->
# Browser-state reconstruction from events — how do you rebuild URL/tabs/screenshot state for a session someone else drove?

**Source:** browser-use MIT `main@3c989dc`; Codebase Memory `browser-use`. **Question:** how do you recover "where is the browser now" (for history/GIF/judging) from tool outputs and browser lifecycle events that were never designed as a state feed?

## Connected graph-selected seam
**Path/Symbol:** `browser_use/beta/service.py` — `_browser_state_from_events` (:2908); recursive candidate miner `_browser_state_candidates` (:2852) with `_browser_url` (:2841), `_internal_browser_endpoint_url` (:2848), 50k-char scan cap; browser_script code mining `_browser_script_navigation_candidates` :2900 (URL_PATTERN over `goto_url|new_tab|open_tab|navigate(` calls); screenshot tail `_screenshot_path_from_events` (:3010).
**Signature:** `_browser_state_from_events(events) -> BrowserStateHistory(url, title, tabs, interacted_element=[], screenshot_path)`.
**Data Shape:** accepted state events: `browser.connected/reconnected/target_changed/live_url/page/state`; tool payloads scanned: `tool.output/tool.started/browser_script.*`. Candidate tuple = `(url, title, target_id)` with target fallbacks `target_id|targetId|tab_id|tabId` → nested `target.*` → `'tab-{idx}'`.

### Decisive source
```python
# URLs are mined from ANY string field — including inside JSON-ish text:
segments.extend(line.strip() for line in text.splitlines()
                if line.strip().startswith(('{','[')))
parsed = None
for parser in (json.loads, ast.literal_eval):   # Python-repr dicts from prints too
    try: parsed = parser(segment); break
    except (SyntaxError, ValueError, TypeError, json.JSONDecodeError): continue
# internal endpoints are noise, not state:
if payload.get('name') == 'browser' and _internal_browser_endpoint_url(candidate_url):
    continue   # http(s)://127.0.0.1|localhost|::1 with empty '/' path
# reconnection must not strand the stale page URL:
next_url = _browser_url(payload.get('live_url')) or _browser_url(payload.get('url'))
if event_type in {'browser.connected','browser.reconnected'} and _internal_browser_endpoint_url(next_url):
    next_url = ''
```

**Flow:** single forward pass; every accepted candidate REPLACES the current url/title/tabs (last-wins), lifecycle `tabs[]` lists replace wholesale when non-empty; if only url/title survived, synthesize one tab `target_id='tab-0'`; screenshot_path is the LAST image seen across `tool.image` / `tool.output.failed.images`; browser_script navigation intent is read from the script SOURCE at `tool.started` time (so pre-execution steps still record destination).
**Invariant:** localhost/127.0.0.1/::1 bare-path endpoints (the debugging bridge itself) never become page state; printed Python dict reprs (`ast.literal_eval`) are first-class candidates because browser_scripts print them; last-event-wins gives monotonic "current" semantics without timestamps.
**Probe:** `tests/ci/test_beta_agent.py:6457` `test_rust_history_uses_printed_browser_script_page_info_as_state`, `:6405` `test_rust_history_uses_browser_script_lifecycle_outputs_as_result`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "browser-use", query: "_browser_state_from_events _browser_state_candidates ast.literal_eval", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the candidate-mining pass + internal-endpoint filter + last-wins fold whenever you must reconstruct UI state from logs; adapt event names and the parser pair; omit browser_script source mining if your tools don't embed navigation calls.
