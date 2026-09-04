<!-- capsule-v2 -->
# Sales Nav pagination & scroll — how do I walk Sales Navigator result pages and load lazy cards without losing rows?

**Source:** maximo3k-sales-nav-scraper GPL-3 `main@bdcd2e5197929f78631ab127d2fd10cee18807ca`; hassan-sales-nav-profiles-scraper NO-LICENSE `main@e294ac09` (learn-only, pattern recorded not copied); linvo-scraper MIT `main@cfbe91080c7347591dee44a26f55d74bba734da2`. Codebase Memory projects `hassan-sales-nav-profiles-scraper`, `linvo-scraper` (maximo3k entry dropped in the 2026-09 stale-index cleanup; its evidence is source-pinned in this capsule and `na-preserving-row-extraction.md`). **Question:** which element gates page-turns, which container scrolls, and what waits must precede extraction?

## scrape_results_page loop + container scroll
**Path/Symbol:** `prospect_scraper_sales_navigator.py:scrape_results_page` (:124–153), `scroll_extract` (:57–122); hassan variant: `linkedin_scraper.py:main` (:116–170 two-stage readiness + one-shot collection, :237–251 page gate); linvo API-side variant: `lib/linkedin/linkedin.sales.page.service.ts:LinkedinSalesPageService.pagesTask` (:15–197).
**Signature:** `scrape_results_page(driver)` — infinite while-loop; per-card `scroll_extract(driver, items)` re-locates by index after scrolling.
**Data Shape:** card list = `li.artdeco-list__item.pl3.pv3`; fields via `span/a[data-anonymize=…]{person-name,title,company-name,location}`; page gate = `button.artdeco-pagination__button--next` enabled-state.

### Decisive source
```python
WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, ".artdeco-list")))
time.sleep(4)                                    # fixed settle AFTER presence — presence ≠ rendered
li_elements = driver.find_elements(By.CSS_SELECTOR, "li.artdeco-list__item.pl3.pv3")
scroll_extract(driver, li_elements)
next_button = driver.find_element(By.CSS_SELECTOR, "button.artdeco-pagination__button--next")
if next_button.is_enabled(): next_button.click() # disabled/absent = last page (NoSuchElementException → break)
else: break

# hassan page rhythm: weak nav event ON PURPOSE — DCL goto, then the ANCHOR wait is the real data gate
page.goto(search_url, wait_until="domcontentloaded")
try:
    page.wait_for_selector('a[data-control-name="view_lead_panel_via_search_lead_name"]', timeout=20000)
except Exception:
    break                                        # stop #1: anchor never mounted ⇒ end of results
page.wait_for_selector('#search-results-container', timeout=10000)
# hassan: the results live in a SCROLLABLE DIV — scroll it, never window.scrollTo:
for _ in range(10):
    page.evaluate("document.querySelector('#search-results-container').scrollTop += 800")
    time.sleep(3)
time.sleep(5)                                    # settle BEFORE the single collection snapshot
elements = page.locator('a[data-control-name="view_lead_panel_via_search_lead_name"]').all()
if not elements: break                           # stop #2: zero cards mounted after scroll+settle
# ... per-row island appends rows ...
if next_button.count() > 0 and not next_button.first.is_disabled():
    next_button.first.click(); time.sleep(2); page_num += 1
else:
    break                                        # stop #3: gate absent or disabled = last page
# linvo: server truth beats DOM — intercept the JSON response instead of parsing cards
const res = await page.waitForResponse(p => /* json with firstName+elements, or <code> HTML embedding */);
const { paging, elements } = json;
pages: Math.ceil((paging.total > 2500 ? 2500 : paging.total) / 25)   // hard cap 2500 results
```

**Flow:** wait for list → settle wait → collect cards → per card: scrollIntoView → visibility wait → RE-LOCATE element by index (stale-reference defense) → extract fields with NA defaults → append batch to CSV → click enabled Next or stop. hassan rhythm: DCL goto → 20 s anchor gate (timeout ⇒ stop) → container scroll ×10 @3 s → 5 s settle → ONE `.all()` snapshot → islanded rows → enabled-Next click or stop.
**Invariant:** four defenses against virtualized/lazy lists — (1) scroll the results CONTAINER not the window (hassan), (2) re-find elements after any scroll (maximo3k :74; hassan collects ONE `.all()` snapshot only AFTER scroll+settle completes, never during scrolling), (3) trust the pagination button's enabled state over result counts, (4) navigation event ≠ data-completeness: hassan's `domcontentloaded` goto is safe ONLY because an explicit 20 s anchor-selector wait (:149) is the actual gate — compensate a weak nav event with a strong element gate, or pay idle-readiness (contrast networkidle2-readiness-gate, whose null-preserving consumers cannot distinguish missing-vs-empty and therefore need networkidle). Termination is three OBSERVED STATES (anchor-wait timeout :149–152, zero-element post-scroll snapshot :168–170, disabled/absent Next :243–248), never a page counter — sales-nav-lead-identity pins stop #1 for the identity flow. Linvo's cap at 2500 mirrors LinkedIn's own search ceiling.
**Probe:** no tests in either repo — coverage caveat recorded (source-grounded). Cross-check: linvo `pagesTask` resolves in graph (`LinkedinSalesPageService.pagesTask`); maximo3k symbols pinned from the recorded checkout (`scroll_extract`, `write_results_to_csv`). hassan greps executed at pin `e294ac09c9b9`: `wait_until=` ⇒ :116 only; `for _ in range(10)` ⇒ :159 only; `time.sleep(5)` ⇒ :164 only; `No profiles found` ⇒ :169 only.

## Get live surrounding code
**Retrieve:**
```ts
// maximo3k index removed 2026-09: probe the pinned checkout via
// `grep -n "scrape_results_page" prospect_scraper_sales_navigator.py` (pin 67596561...).
await mcp.codebase_memory.search_graph({ project: "linvo-scraper", query: "pagesTask", limit: 5 });
// hassan (executed pass 2): name_pattern "^main$" ⇒ …linkedin_scraper.main Function :33–259
```

## Verdict
Adopt enabled-button-gated pagination + container-scoped scrolling + index re-location; adapt selectors, settle times, and output sinks to host; omit hard-coded Google-Sheet IDs / AdsPower keys / `'prospects_1.csv'`. Caveat: all claims source-grounded; none test-pinned upstream.
