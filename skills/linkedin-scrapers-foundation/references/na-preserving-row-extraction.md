<!-- capsule-v2 -->
|# NA-preserving row extraction — how do I scrape Sales Nav list cards field-by-field so a broken card yields a complete-but-partial row instead of losing the prospect?

**Source:** maximo3k-sales-nav-scraper GPL-3 `main@bdcd2e5` (2024-07-01); Codebase Memory `maximo3k-sales-nav-scraper`. **Question:** when each result card has 5 independently-missing fields, what per-card contract keeps the output schema total (every row, all columns) and the pagination loop honest about the last page?

## Pre-initialized NA fields + scrollIntoView + re-find by index + three-way Next gate
**Path/Symbol:** `prospect_scraper_sales_navigator.py:scroll_extract` (:57–122), `scrape_results_page` (:124–153), `write_results_to_csv` (:22–29).
**Signature:** `scroll_extract(driver, items) -> None` (writes CSV as side effect); `write_results_to_csv(results, filename)` — appends header ONLY when `file.tell() == 0`.
**Data Shape:** row dict with FIVE pre-initialized keys — `{person_name, person_title, person_company, person_location, person_link}` each defaulting to `"NA"` BEFORE any extraction; card selector `li.artdeco-list__item.pl3.pv3`; field selectors are all `data-anonymize` attributes (`person-name`, `title`, `company-name`, `location`).

### Decisive source
```python
# PER-CARD ISOLATION: defaults exist BEFORE try — a mid-field failure still
# emits a full-width row with NA in every un-extracted column
person_name = "NA"; person_title = "NA"; person_company = "NA"
person_location = "NA"; person_link = "NA"
try:
    driver.execute_script("arguments[0].scrollIntoView(true);", item)   # lazy-load trigger
    WebDriverWait(driver, 10).until(EC.visibility_of(item))
    # RE-FIND BY INDEX: stale element after virtualized re-render
    item = driver.find_elements(By.CSS_SELECTOR, "li.artdeco-list__item.pl3.pv3")[index]
    person_name    = item.find_element(By.CSS_SELECTOR, "span[data-anonymize='person-name']").text
    link_element   = name_element.find_element(By.XPATH, "..")           # parent <a> carries href
    person_link    = link_element.get_attribute('href')
    person_title   = item.find_element(By.CSS_SELECTOR, "span[data-anonymize='title']").text
    person_company = item.find_element(By.CSS_SELECTOR, "a[data-anonymize='company-name']").text
    person_location= item.find_element(By.CSS_SELECTOR, "span[data-anonymize='location']").text
    results.append({...all five keys...})
except Exception:
    results.append({...all five keys, untouched NA defaults...})         # NEVER drop the row

# THREE-WAY PAGINATION GATE: enabled → click / disabled or absent → honest stop
next_button = driver.find_element(By.CSS_SELECTOR, "button.artdeco-pagination__button--next")
if next_button.is_enabled(): next_button.click()
else: print("Next button not enabled, last page reached."); break     # disabled = real last page
except NoSuchElementException: break                                   # absent = no pagination at all

def write_results_to_csv(results, filename):
    if file.tell() == 0: writer.writerow([header])                     # empty-file probe, not os.path.exists
```
**Flow:** wait `.artdeco-list` (+4 s settle) → collect card elements → per card: scrollIntoView → visibility wait → re-find by index → five scoped field reads with NA fallbacks → append row → flush batch to CSV → Next-button trichotomy → repeat.
**Invariant:** every iteration appends exactly one schema-complete row — extraction failure degrades FIELD VALUES ("NA"), never ROW COUNT, so downstream join/analysis code never sees ragged data; the header is written on the empty-file probe (`tell()==0`) not on path existence, so appending to an existing file never duplicates headers; pagination stops on DISABLED-or-ABSENT next (both terminal states distinguished only in logs) — it never guesses a page count; elements are re-queried after scroll because Sales Nav's virtualized list invalidates earlier references.
**Probe:** repo has no automated tests — coverage caveat. Deterministic probes: `grep -c '"NA"' prospect_scraper_sales_navigator.py` ⇒ 10 (5 defaults + 5 except-path re-lists); `grep -n "tell() == 0" prospect_scraper_sales_navigator.py` ⇒ :25; graph anchor `scrape_results_page` resolves in project `maximo3k-sales-nav-scraper`.
**Retrieve:** `await mcp.codebase_memory.search_graph({ project: "maximo3k-sales-nav-scraper", query: "scroll_extract scrape_results_page write_results_to_csv artdeco", limit: 5 });`

## Verdict
Adopt: pre-initialized NA defaults inside the per-item try scope, the tell()==0 header probe for append-mode CSVs, index-based element re-find after scroll, and the enabled/disabled/absent Next trichotomy. Adapt field selectors to current Sales Nav markup (`data-anonymize` attributes rotate); swap print-noise for the string-outcome-channel ledger. Omit the hard-coded 4 s/1 s sleeps in favor of humanization-scroll's bounded disciplines when porting at scale. Contrast: hassan variant extracts IDENTITY from row attributes and treats fields other than name as optional; this pattern extracts the FULL FIELD SET and treats identity as just another nullable column — choose based on whether the consumer needs canonical URLs (hassan) or wide rows (this). dedupe-applied-tracking cites this file's writer; THIS capsule covers its reader-side completeness contract.
