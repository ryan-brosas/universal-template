<!-- capsule-v2 -->
# Stale-element re-find — re-locate each card by index before touching its fields

**Source:** maximo3k-sales-nav-scraper (license file, `main@bdcd2e5197929f78631ab127d2fd10cee18807ca`); Codebase Memory `maximo3k-sales-nav-scraper`. **Question:** How does the extraction loop keep working when Selenium raises `StaleElementReferenceException` after the page re-renders under the loop?

## Re-locate by index inside the try
**Path/Symbol:** `prospect_scraper_sales_navigator.py:scroll_extract` (line 74).
**Signature:** `item = driver.find_elements(By.CSS_SELECTOR, "li.artdeco-list__item.pl3.pv3")[index]`.
**Data Shape:** `items` was collected once per page by the caller (`scrape_results_page`, line 133) and is already stale-prone by the time per-item work starts; `index` is the enumerate position of the original element. The re-found element replaces the local `item` binding for all subsequent field reads.

### Decisive source
```python
for index, item in enumerate(items):
    ...
    driver.execute_script("arguments[0].scrollIntoView(true);", item)
    WebDriverWait(driver, 10).until(EC.visibility_of(item))
    item = driver.find_elements(By.CSS_SELECTOR, "li.artdeco-list__item.pl3.pv3")[index]
```

**Flow:** for each originally-collected card: scroll IT into view → wait for ITS visibility → immediately re-query the whole card list and take position `index` → do all field reads against that fresh element.
**Invariant:** the scroll/visibility wait runs against the ORIGINAL element, but every field read runs against the RE-FOUND one — the two elements must refer to the same card, which holds only while the DOM list order is stable during a page's extraction. A porter who re-finds without matching the caller's exact selector (`li.artdeco-list__item.pl3.pv3`) or who reorders cards mid-page will extract from the wrong card; index-based re-location assumes no card is inserted/removed mid-extraction.
**Probe:** no test files exist in the repo — source-grounded evidence only (coverage caveat). Observable boundary: line 74 overwrites `item` between the visibility wait and the first field read.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "maximo3k-sales-nav-scraper", query: "find_elements artdeco-list__item index scroll_extract", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt scroll-original-then-re-find-by-index as the stale-element countermeasure — it survives Sales Navigator's lazy re-renders without retry loops or explicit exception handling for staleness. Adapt the selector to whatever the host page uses, keeping caller and re-find selectors IDENTICAL. Omit the assumption that the card list is immutable mid-page if the target DOM mutates order. No-test caveat applies.
