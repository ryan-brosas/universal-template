<!-- capsule-v2 -->
# Selenium click/find helper ladder — how do I build a tolerant Selenium helper layer that clicks text-labeled spans, toggles boolean switches, and scrolls elements into view without brittle selectors?

**Source:** Auto_job_applier_linkedIn MIT `main@0ca5550f8aa80027621cfc17a30fceba05705f84` (`modules/clickers_and_finders.py` 166L). Codebase Memory `Auto_job_applier_linkedIn`. **Question:** what is the normalized-text XPath click helper and the try-* tolerant find ladder that keeps a Selenium automation resilient to LinkedIn's changing DOM?

## Text-span click + tolerant find ladder
**Path/Symbol:** `modules/clickers_and_finders.py:wait_span_click` (:28–48), `multi_sel` (:50–64), `multi_sel_noWait` (:66–81), `boolean_button_click` (:83–95), `try_xp` (:126–133), `try_linkText` (:135–137), `try_find_by_classes` (:139–143), `scroll_to_view` (:105–114), `text_input_by_ID` (:117–124). **Signature:** `wait_span_click(driver, text, time=5.0, click=True, scroll=True, scrollTop=False) -> WebElement | bool`; `try_xp(driver, xpath, click=True) -> WebElement | bool`.
**Data Shape:** clicks are keyed by normalized visible text via `By.XPATH, './/span[normalize-space(.)="<text>"]'`; boolean toggles are found as `input[@role="switch"]` under an `h3:normalize-space()="<text>"/ancestor::fieldset`; every find returns a falsy sentinel (`False`/`None`) instead of raising.

### Decisive source
```python
def wait_span_click(driver, text, time=5.0, click=True, scroll=True, scrollTop=False):
    if text:
        try:
            button = WebDriverWait(driver, time).until(
                EC.presence_of_element_located(
                    (By.XPATH, './/span[normalize-space(.)="'+text+'"]')))
            if scroll: scroll_to_view(driver, button, scrollTop)
            if click:
                button.click(); buffer(click_gap)
            return button
        except Exception:
            print_lg("Click Failed! Didn't find '"+text+"'")
            return False

def try_xp(driver, xpath, click=True):
    try:
        if click:
            driver.find_element(By.XPATH, xpath).click(); return True
        else:
            return driver.find_element(By.XPATH, xpath)
    except: return False

def try_find_by_classes(driver, classes):
    for cla in classes:
        try: return driver.find_element(By.CLASS_NAME, cla)
        except: pass
    raise ValueError("Failed to find an element with given classes")
```

**Flow:** for a labeled action, `wait_span_click` waits up to `time` for a span whose normalized text equals the label, optionally scrolls it to center view (smooth behavior from config), clicks, and sleeps `buffer(click_gap)`; `multi_sel`/`multi_sel_noWait` fan out over a list of labels (with/without wait); `boolean_button_click` climbs from an `<h3>` heading to its `fieldset` and clicks the `input[@role="switch"]` via ActionChains; `try_*` helpers attempt a find and return a falsy sentinel on failure so callers can branch instead of crashing.
**Invariant:** every helper returns a falsy sentinel (`False`/`None`) on failure — never raises — so a missing element degrades to a logged skip, not a crash. Text matching uses `normalize-space(.)` (collapses whitespace) so label text with extra spaces still matches. Inputs are cleared before typing (`Keys.CONTROL + "a"` then value) to replace, not append. `scroll_to_view` centers the element (`block: "center"`) with configurable smooth/instant behavior.
**Probe:** no upstream tests — coverage caveat recorded. Graph anchors resolve: `wait_span_click`, `try_xp`, `try_find_by_classes`, `scroll_to_view`, `check_int`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "Auto_job_applier_linkedIn", query: "wait_span_click", limit: 5 });
await mcp.codebase_memory.search_graph({ project: "Auto_job_applier_linkedIn", query: "try_xp", limit: 5 });
```

## Verdict
Adopt the normalized-text XPath click helper, the falsy-sentinel try ladder, and the clear-then-type input discipline; adapt the label strings and the `input[@role="switch"]` selector (rot against live LinkedIn); omit the pyautogui desktop hacks and the `company_search_click` filter-specific flow (source-specific). Caveat: source-grounded only, no test coverage.
