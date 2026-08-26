<!-- capsule-v2 -->
# Pagination — page through Sales Navigator results on the enabled Next button

**Source:** maximo3k-sales-nav-scraper (license file, `main@bdcd2e5197929f78631ab127d2fd10cee18807ca`); Codebase Memory `maximo3k-sales-nav-scraper`. **Question:** How does the scraper advance across Sales Navigator saved-search result pages without over-running the last one?

## Pagination loop
**Path/Symbol:** `prospect_scraper_sales_navigator.py:scrape_results_page` (lines 124–153).
**Signature:** `def scrape_results_page(driver) -> None`.
**Data Shape:** a live Selenium `driver`; reads the `.artdeco-list` container and the `button.artdeco-pagination__button--next` pagination control; mutates the driver's current page.

### Decisive source
```python
while True:  # Loop through all pages
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, ".artdeco-list")))
    time.sleep(4)
    li_elements_no_soup = driver.find_elements(By.CSS_SELECTOR, "li.artdeco-list__item.pl3.pv3")
    scroll_extract(driver, li_elements_no_soup)
    try:
        next_button = driver.find_element(By.CSS_SELECTOR, "button.artdeco-pagination__button--next")
        if next_button.is_enabled():
            next_button.click()
        else:
            break
    except NoSuchElementException:
        break
    except Exception as e:
        break
```

**Flow:** wait for the results list → settle → extract the current page's cards → locate the Next button → click it only if `is_enabled()` → else stop; a missing or erroring Next button also stops the loop.

**Invariant:** the loop never advances past the last page — it terminates on a disabled, absent, or erroring Next button, and never clicks a disabled control.

**Probe:** no test files exist in the repo; this is source-grounded only (coverage caveat). The observable boundary is `is_enabled()` gating the click.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "maximo3k-sales-nav-scraper", query: "scrape_results_page pagination next", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the enabled-button-gated pagination loop (wait → settle → extract → click-if-enabled → break otherwise). Adapt the wait/settle timings and the pagination selector to the host and current LinkedIn DOM. Omit the hard-coded `time.sleep(4)` cadence unless a target needs it.
