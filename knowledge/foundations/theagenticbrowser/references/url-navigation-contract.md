<!-- capsule-v2 -->
# URL normalization ladder — where must protocol defaulting live when three layers all navigate?

**Source:** TheAgenticBrowser (TheAgentic Community License 1.0) `main@71daa28`; Codebase Memory `mnt-hdd-utopia-inspo-TheAgenticBrowser`. **Question:** Users type "google.com", tools receive URLs from search results — who adds https:// and does re-navigation get skipped?

## ensure_protocol at every boundary + same-URL short-circuit + 250-char display cap
**Path/Symbol:** `open_url.py`:`ensure_protocol` (:64-78), same-URL check :36-39; `browser_manager.py`:`navigate_to_url` :168-178; `orchestrator.py`:`navigate_to_url` :233-241 + start_url handling :286-287; `get_url.py`:40-43.
**Signature:** `def ensure_protocol(url: str) -> str`.
**Data Shape:** Default scheme https://; openurl takes optional extra `timeout` seconds (goto timeout=timeout*1000).

### Decisive source
```python
# openurl: skip reload when already there
if page.url == url:
    result += f"Page already loaded: {url}, Title: {title}"
else:
    await page.goto(url, timeout=timeout*1000)

except PlaywrightTimeoutError as pte:
    logger.warn(f"Initial navigation to {url} failed: {pte}. Will try to continue anyway.")
    result += f"Page loaded with timeout: {url}"      # NOT an error to the agent
```
All three navigators independently guard with `startswith(('http://','https://'))` before prepending https:// — orchestrator's own copy (:237), manager's (:172), and ensure_protocol in openurl.
**Flow:** planner/agent supplies bare domain → any layer normalizes → goto with short client-side budget → timeout degrades to success-with-caveat string (slow SPA pages keep loading while the agent proceeds to DOM work).
**Invariant:** Timeout-on-navigation is deliberately NON-fatal: domcontentloaded usually fired, so reporting failure would waste a whole loop iteration on a working page. The triple-duplicated protocol guard is defensive redundancy — removing it from any single layer breaks direct calls into that layer. Same-URL short-circuit prevents pointless reloads that would drop form state mid-task.
**Probe:** No tests (coverage caveat). Graph pin: `ensure_protocol` resolves as its own graph node with inbound edge from openurl only; semantic search ranks openurl+ensure_protocol adjacent (:search probe in work record).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-TheAgenticBrowser", query: "ensure_protocol openurl navigate", limit: 10, fields: ["name", "file"] });
```

## Verdict
Adopt normalize-at-every-boundary plus timeout-as-soft-success for navigation tools. Adapt the extra-timeout budget to your targets. Omit the duplication once you control all callers — centralize in one navigation module instead.
