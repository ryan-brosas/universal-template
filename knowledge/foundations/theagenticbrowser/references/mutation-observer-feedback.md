<!-- capsule-v2 -->
# DOM-mutation feedback loop — how does an action tool tell the agent "your click opened something new" instead of reporting success?

**Source:** TheAgenticBrowser (TheAgentic Community License 1.0) `main@71daa28`; Codebase Memory `mnt-hdd-utopia-inspo-TheAgenticBrowser`. **Question:** After clicking/typing/keypressing, how do you detect side-effect UI (menus, autocomplete, modals) appearing and route it back into the agent's action result?

## Page-side MutationObserver → exposed bridge → Python pub-sub → result-string rewrite
**Path/Symbol:** `core/utils/dom_mutation_observer.py`:`add_mutation_observer`, `subscribe`, `unsubscribe`, `dom_mutation_change_detected` (whole file, 87L); consumers in `click_using_selector.py:45-58`, `enter_text_using_selector.py:130-159`, `press_key_combination.py:43-66`.
**Signature:** `subscribe(callback: Callable[[str], None]) -> None`; `async def add_mutation_observer(page: Page)`.
**Data Shape:** JS pushes JSON `[{'tag': ..., 'content': ...}]` through `window.dom_mutation_change_detected` (an `expose_function` bridge installed once per page); Python parses it and fans out to a module-level callback list. Filters: skip SCRIPT/NOSCRIPT/STYLE tags, skip anything inside the agent's own overlay (`#agentDriveAutoOverlay`), dedupe characterData changes by content containment, require non-empty trimmed innerText.

### Decisive source
```python
# every mutating skill wraps its action like this:
dom_changes_detected = None
def detect_dom_changes(changes):
    nonlocal dom_changes_detected
    dom_changes_detected = changes
subscribe(detect_dom_changes)
result = await do_click(page, selector, wait_before_execution)
await asyncio.sleep(0.1)              # let the observer fire before unsubscribing
unsubscribe(detect_dom_changes)
...
if dom_changes_detected:
    return f"Success: {result['summary_message']}.\n As a consequence of this action, new elements have appeared in view: {dom_changes_detected}. This means that the action to click {selector} is not yet executed and needs further interaction. Get all_fields DOM to complete the interaction."
```
The observer itself only watches `childList` + `characterData` mutations (style/class-only visibility toggles are NOT detected — recorded limitation in the source comment).

**Flow:** navigation handler re-installs the observer on every domcontentloaded → skill subscribes → action runs → fixed 100 ms drain sleep → unsubscribe → if changes arrived, the SUCCESS string is rewritten into "not yet executed, fetch the new DOM" guidance.
**Invariant:** Three things break silently if ported wrong: (1) the 100 ms sleep must happen BEFORE unsubscribe or late mutations race the teardown; (2) callbacks are module-level globals — subscribe/unsubscribe pairs must be exception-safe or stale closures leak between actions; (3) the overlay MUST be excluded from observation or the agent observes its own UI and loops forever. The rewritten message deliberately claims the action "is not yet executed" — this pessimism is the feature that stops the LLM from declaring victory over an unsubmitted form.
**Probe:** No tests (coverage caveat). Graph pin: `trace_path --function-name subscribe --direction inbound` lands click/enter_text/press_key skills; the overlay exclusion id `agentDriveAutoOverlay` also appears in the a11y reconciler's `ids_to_ignore`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-TheAgenticBrowser", query: "subscribe mutation observer dom change", limit: 10, fields: ["name", "file"] });
```

## Verdict
Adopt the observe-window + result-rewrite contract for every state-changing browser tool. Adapt the 100 ms window to your latency budget and the content filters to your overlay id. Omit Playwright's auto-waiting as a substitute — it cannot see *newly appearing* interactive surfaces the way a mutation feed can.
