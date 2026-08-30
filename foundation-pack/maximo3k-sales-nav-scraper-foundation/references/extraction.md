<!-- capsule-v2 -->
# Extraction — scroll each card into view and pull the five data-anonymize fields with NA defaults

**Source:** maximo3k-sales-nav-scraper (license file) `main@bdcd2e5197929f78631ab127d2fd10cee18807ca`; Codebase Memory `maximo3k-sales-nav-scraper`. **Question:** How does a Selenium loop reliably extract person name/title/company/location/link from each Sales Navigator result card without failing the whole run on one bad card?

## Per-card scroll + data-anonymize extraction
**Path/Symbol:** `prospect_scraper_sales_navigator.py:scroll_extract` (57–122).
**Signature:** `def scroll_extract(driver, items)` — builds a LOCAL `results` list, persists it via `write_results_to_csv(results, 'prospects_1.csv')` (:120), returns `None`.
**Data Shape:** `results` is created fresh per call (`results = []` at :58) — NOT module state; each entry is a five-key dict (`person_name/title/company/location/link`). Every field is pre-set to the string `"NA"` and overwritten only by a successful read; a per-card exception appends an all-NA row instead of aborting.

### Decisive source
```python
results = []
for index, item in enumerate(items):
    person_name = person_title = person_company = person_location = person_link = "NA"
    try:
        driver.execute_script("arguments[0].scrollIntoView(true);", item)
        WebDriverWait(driver, 10).until(EC.visibility_of(item))
        item = driver.find_elements(By.CSS_SELECTOR, "li.artdeco-list__item.pl3.pv3")[index]
        name_element = item.find_element(By.CSS_SELECTOR, "span[data-anonymize='person-name']")
        person_name = name_element.text if name_element else "NA"
        link_element = name_element.find_element(By.XPATH, "..")
        person_link = link_element.get_attribute('href') if link_element else "NA"
        title_element = item.find_element(By.CSS_SELECTOR, "span[data-anonymize='title']")
        person_title = title_element.text if title_element else "NA"
        company_element = item.find_element(By.CSS_SELECTOR, "a[data-anonymize='company-name']")
        person_company = company_element.text if company_element else "NA"
        location_element = item.find_element(By.CSS_SELECTOR, "span[data-anonymize='location']")
        person_location = location_element.text if location_element else "NA"
        results.append({'person_name': person_name, ..., 'person_link': person_link})  # extracted
        time.sleep(1)
    except Exception as e:
        print(f"Failed to process item at index {index}: {str(e)}")
        results.append({'person_name': person_name, ..., 'person_link': person_link})  # all-NA defaults
write_results_to_csv(results, 'prospects_1.csv')
```

**Flow:** initialize all fields to `"NA"` → scroll the card into view and wait for visibility → re-locate the card by index → read each `data-anonymize` field → the SUCCESS append happens INSIDE the try (:99–105); on ANY exception the EXCEPT handler logs and appends the all-NA row (:112–118) — exactly one append executes per card; after the loop one CSV write persists the page's rows.
**Invariant:** one malformed card never aborts the run — it yields an all-NA row, never a PARTIAL row: `find_element` RAISES on an absent field, so any missing field routes the whole card to the except branch and the per-field `else "NA"` fallbacks are unreachable for missing elements. The link is derived from the parent of the name element, not a direct attribute.
**Probe:** no test file exists in the repo — this is source-grounded evidence only (coverage caveat).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "maximo3k-sales-nav-scraper", query: "scroll_extract data-anonymize scrollIntoView", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the scroll-into-view + re-locate-by-index + `data-anonymize` extraction with per-field `"NA"` defaults and per-card exception tolerance. Adapt the CSS selectors and the name-element parent link derivation to the current LinkedIn DOM. Omit the 1-second per-card sleep and the fixed re-location-by-index assumption unless a target needs them.
