<!-- capsule-v2 -->
# Overlay-visibility DOM text extraction — how do you get clean page text when your own UI is injected into the page?

**Source:** TheAgenticBrowser (TheAgentic Community License 1.0) `main@71daa28`; Codebase Memory `mnt-hdd-utopia-inspo-TheAgenticBrowser`. **Question:** When your agent injects a persistent overlay into every page, how do you extract body text the LLM sees without feeding it your own chrome?

## In-page hide → innerText + alt-text collect → visibility revert, all in ONE evaluate
**Path/Symbol:** `core/skills/get_dom_with_content_type.py`:`get_filtered_text_content` (`:91-125`), wrapped by `get_dom_texts_func` (`:16-59`, BA tool `get_dom_text` at `browser_agent.py:265-268`).
**Signature:** `async def get_filtered_text_content(page: Page) -> str`.
**Data Shape:** JS side takes zero args; reads/writes inline `style.visibility` only. Python side writes the result to disk (`SOURCE_LOG_FOLDER_PATH/text_only_dom.txt`) and returns the string to the LLM.

### Decisive source
```javascript
// :95-122 — one atomic page.evaluate:
const selectorsToFilter = ['#tawebagent-overlay'];
const originalStyles = [];
selectorsToFilter.forEach(selector => {
    const elements = document.querySelectorAll(selector);
    elements.forEach(element => {
        originalStyles.push({ element: element, originalStyle: element.style.visibility });
        element.style.visibility = 'hidden';
    });
});
let textContent = document?.body?.innerText || document?.documentElement?.innerText || "";
let altTexts = Array.from(document.querySelectorAll('img')).map(img => img.alt);
altTexts = "Other Alt Texts in the page: " + altTexts.join(' ');
originalStyles.forEach(entry => {
    entry.element.style.visibility = entry.originalStyle;
});
return textContent + " " + altTexts;
```
**Flow:** `get_dom_texts_func` → `wait_for_non_loading_dom_state(page, 2000)` (:47; readyState poll every 50 ms capped at 2 s — NOT a full load wait) → single `page.evaluate` that hides `#tawebagent-overlay`, snapshots `document.body.innerText` (+ documentElement fallback), joins ALL `<img alt>` after a literal `"Other Alt Texts in the page: "` prefix, reverts visibilities, returns concatenated string → written to `text_only_dom.txt`, returned as tool output.
**Invariant:** The hide/revert pair must live inside ONE evaluate — splitting them across calls leaks hidden state on exceptions and races the MutationObserver into reporting your own style writes as page changes. `innerText` (not textContent) is load-bearing: it respects CSS visibility/layout, which is exactly why hiding works. Alt texts are appended with their prefix so the LLM can attribute them. This is the third leg of overlay hygiene alongside pass-1's mutation-observer self-exclusion and dom-prune filtering.
**Probe:** `grep -c "selectorsToFilter" core/skills/get_dom_with_content_type.py` → `2`; `grep -c "innerText" core/skills/get_dom_with_content_type.py` → `1`; `grep -c "alt" core/skills/get_dom_with_content_type.py` → `6`; `grep -c "originalStyles" core/skills/get_dom_with_content_type.py` → `3`; `grep -c "text_only_dom.txt" core/skills/get_dom_with_content_type.py` → `1`. Coverage caveat: no upstream tests.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-TheAgenticBrowser", query: "get_filtered_text_content innerText alt overlay", limit: 10, fields: ["name", "file"] });
```

## Verdict
Adopt: single-evaluate hide→collect→revert over `innerText` with prefixed alt-text appendix. Adapt: the overlay selector id and evidence-file path. Omit: logfire timing logs. Coverage caveat: no upstream tests; probes line-pinned at pin `71daa28`.
