<!-- capsule-v2 -->
# Parallel extraction kernel — how do you fire eight browser extractions at once, degrade each slot independently, and retry only transient failures?

**Source:** cuga-agent Apache-2.0 `main@5de53ade77c36166da6ace906af488b2b445454f`; Codebase Memory `mnt-hdd-utopia-inspo-cuga-agent`. **Question:** How do you run N page-extraction calls concurrently where any single failure degrades to a typed default instead of failing the batch?

## full_extract_chrome_extension gather + transient-only retry
**Path/Symbol:** `src/cuga/backend/browser_env/browser/gym_obs/extract_chrome_extension.py:full_extract_chrome_extension` (415–517); join helper `:add_browsergym_id_to_accessibility_tree` (343–412).
**Signature:** `async def full_extract_chrome_extension(communicator, tags_to_mark: Literal["all","standard_html"]="standard_html", lenient: bool=False, max_retries: int=3) -> Dict[str, Any]`.
**Data Shape:** returns a 9-key dict (`dom_snapshot`, `accessibility_tree`, `dom_tree`, `extra_properties`, `focused_element_bid`, `screenshot`, `page_content`, `page_url`, `page_title`); failed slots become `{}` (dict slots) or `""` (string slots) — never None, never exceptions.

### Decisive source
```python
# extract_chrome_extension.py:441-462 — parallel gather with per-slot exception→default demotion
results = await asyncio.gather(*tasks, return_exceptions=True)
dom_snapshot = results[0] if not isinstance(results[0], Exception) else {}
accessibility_tree = results[1] if not isinstance(results[1], Exception) else {}
...
screenshot = results[4] if not isinstance(results[4], Exception) else ""
...
# :483-496 — retry ONLY whitelisted transient extension error strings; lenient forced on FINAL try
except (ChromeExtensionError, MarkingError) as e:
    err_msg = str(e)
    if retry < max_retries - 1 and any(
        msg in err_msg
        for msg in ["Frame was detached", "Frame with the given frameId is not found",
                    "Execution context was destroyed", "Frame has been detached",
                    "Chrome extension connection timeout"]):
        await _post_extract_chrome_extension(communicator)
        await asyncio.sleep(0.5)
        continue
    else:
        raise e
```
(`_pre_extract_chrome_extension(..., lenient=(retry == max_retries - 1))` at 436-438 forces lenient marking mode on the last attempt.)

**Flow:** mark DOM (`mark_elements`) → 8 extraction tasks via `asyncio.gather(return_exceptions=True)` → per-slot Exception check demotes to typed default while logging → cross-artifact join (`add_browsergym_id_to_accessibility_tree`: accessibility nodes gain `browsergym_id` by correlating `backendDOMNodeId` against the DOM snapshot's string-table attributes, `-1` string index → None sentinel) → `break` on success → `finally` cleanup runs every iteration.
**Invariant:** only the five whitelisted transient strings may trigger a retry — every other failure re-raises immediately; the whole loop body (including marking) reruns on retry, and cleanup is best-effort inside `finally` so a cleanup error can never mask the real result.
**Probe:** no upstream direct test covers this file (grep over `tests/` finds zero) — coverage caveat recorded. Deterministic probe executed against the repo venv pins the demotion shape: a stub communicator whose `extract_screenshot` raises and whose other extract methods return canned values feeds `full_extract_chrome_extension(max_retries=1)` → result has `screenshot == ""`, all other keys populated, no retry.
**Executed:**
```bash
cd $REFERENCE_ROOT/cuga-agent && PYTHONPATH=src .venv/bin/python -c "
import asyncio
from cuga.backend.browser_env.browser.gym_obs.extract_chrome_extension import full_extract_chrome_extension
class Stub:
    async def mark_elements(self, tags_to_mark='standard_html'): return []
    async def unmark_elements(self): pass
for name in ['extract_dom_snapshot','extract_accessibility_tree','extract_dom_tree','extract_focused_element_bid','extract_screenshot','extract_page_content','get_active_tab_url','get_active_tab_title']:
    async def f(self, name=name):
        if name == 'extract_screenshot': raise RuntimeError('boom')
        return {'data': name}
    setattr(Stub, name, f)
r = asyncio.run(full_extract_chrome_extension(Stub(), max_retries=1))
assert r['screenshot'] == '' and r['page_url'] == 'get_active_tab_url' and r['dom_snapshot'] == {'data':'extract_dom_snapshot'}, r
print('OK')
"
```
→ `OK`. (`extract_page_url`/`extract_page_title` wrappers call `get_active_tab_url`/`get_active_tab_title` on the communicator.)

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-cuga-agent", query: "full_extract_chrome_extension add_browsergym_id_to_accessibility_tree gather return_exceptions retry", limit: 10 });
```

## Verdict
Adopt gather-with-per-slot-defaults as the concurrency pattern for multi-artifact page capture, the whitelist-gated retry ladder with forced-lenient final attempt, and the string-table cross-artifact bid join. Adapt the transient-string list and slot defaults to your extension vocabulary. Omit the commented-out `unmark_elements()` in `_post_extract_chrome_extension` (deliberately disabled). Caveat: source-only evidence; no upstream test.
