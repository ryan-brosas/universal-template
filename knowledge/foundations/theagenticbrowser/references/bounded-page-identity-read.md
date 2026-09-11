<!-- capsule-v2 -->
# Bounded page-identity read — how should a read-only "where am I" tool bound its payload, survive title failures, and map errors?

**Source:** TheAgenticBrowser (TheAgentic Community License 1.0 — source-available; SaaS-competing-use restricted) `main@71daa28`; Codebase Memory `mnt-hdd-utopia-inspo-TheAgenticBrowser`. **Question:** What does a zero-argument page-identity tool owe the loop: how big may its string be, what happens when `page.title()` hangs, and which errors deserve which message?

## geturl — URL+title in one bounded string
**Path/Symbol:** `core/skills/get_url.py`:`geturl` (:6-39; body previously uncited — url-navigation-contract pinned only :40-43). Sole inbound caller: BA wrapper `get_url_tool` (`browser_agent.py:275-279`).
**Signature:** `async def geturl() -> Annotated[str, "Returns the full URL of the current active web site/page."]`.
**Data Shape:** No inputs. Output = `"Current Page: {url}, Title: {title}"`, degrading to `"Current Page: {url}"` when the title read throws; URL hard-truncated at **250 chars + `"..."`**.

### Decisive source
```python
browser_manager = PlaywrightManager(browser_type='chromium', headless=False)  # :19 — args are DEAD: singleton already exists
page = await browser_manager.get_current_page()
if not page:
    raise ValueError('No active page found. OpenURL command opens a new page.')
await page.wait_for_load_state("domcontentloaded")
try:
    title = await page.title()
    current_url = page.url
    if len(current_url) >250:
        current_url = current_url[:250] + "..."
    return f"Current Page: {current_url}, Title: {title}"
except:  # noqa: E722 — title failure is non-fatal; degrade to URL-only
    current_url = page.url
    return f"Current Page: {current_url}"
except Exception as e:   # (outer try at :17) — ALL failures launder into one message
    raise ValueError('No active page found. OpenURL command opens a new page.') from e
```

**Flow:** resolve singleton → None-page ⇒ ValueError → wait for domcontentloaded → title+URL → truncate URL → compose. Title exception ⇒ bare-except fallback string. ANY other exception (including a `page.url` property failure or wait timeout) escapes to the outer handler and is re-raised as the SAME 'No active page found' ValueError.
**Invariant:** The payload bound (250 chars) protects the transcript from pathological URLs — keep it when you port. Title-read failure must never fail the call (URL alone answers "where am I"). KNOWN QUIRK NOT TO COPY: the outer except launders every error into 'No active page found…', so a timeout masquerades as a missing page — porters should map wait-failures distinctly.
**Probe:** `cd $REFERENCE_ROOT/TheAgenticBrowser && grep -n ">250" core/skills/get_url.py` → `:31`; `grep -c "No active page found" core/skills/get_url.py` → `2`; `grep -n "except:" core/skills/get_url.py` → `:34`. Coverage caveat: repo ships no tests.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-TheAgenticBrowser", query: "geturl current page title truncation", limit: 10 });
```

## Verdict
Adopt: one-call identity read returning a bounded `URL + Title` string with graceful title degradation. Adapt: the truncation limit to your transcript budget; replace the singleton constructor args at call sites with nothing (they are dead vocabulary — the args only matter on FIRST construction). Fix-at-port: split the outer exception mapping so navigation-state errors don't all claim 'No active page found'. Caveat: no upstream tests; graph coverage `no_recorded_issue` at generation `2026-08-23T00:02:33Z`.
