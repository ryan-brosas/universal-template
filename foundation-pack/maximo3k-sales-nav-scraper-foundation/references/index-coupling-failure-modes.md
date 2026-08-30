<!-- capsule-v2 -->
# Index-coupling — two independent `find_elements` calls over one mutable list: the failure modes of matching by position

**Source:** maximo3k-sales-nav-scraper (license file, `main@bdcd2e5197929f78631ab127d2fd10cee18807ca`); Codebase Memory `maximo3k-sales-nav-scraper`. **Question:** What breaks, and what does the run cost, when the per-card re-find by index cannot match the caller's snapshot?

## Two find_elements sites bound by enumerate index
**Path/Symbol:** `prospect_scraper_sales_navigator.py` — caller `scrape_results_page`:133; re-find inside `scroll_extract`:74.
**Signature:** both call `driver.find_elements(By.CSS_SELECTOR, "li.artdeco-list__item.pl3.pv3")`; :74 subscripts `[index]` from `enumerate(items)`.
**Data Shape:** the caller materializes ONE snapshot list and iterates its stale-prone elements (:133 → :59); each iteration re-queries the LIVE DOM with the identical selector and takes position `index` (:74). The coupling holds only while the live list is order-stable relative to the snapshot.

### Decisive source
```python
# caller (scrape_results_page):
li_elements_no_soup = driver.find_elements(By.CSS_SELECTOR, "li.artdeco-list__item.pl3.pv3")  # :133
scroll_extract(driver, li_elements_no_soup)

# callee (scroll_extract):
for index, item in enumerate(items):                                                          # :59
    ...
    driver.execute_script("arguments[0].scrollIntoView(true);", item)                          # :69
    WebDriverWait(driver, 10).until(EC.visibility_of(item))                                    # :72
    item = driver.find_elements(By.CSS_SELECTOR, "li.artdeco-list__item.pl3.pv3")[index]       # :74
```

**Flow:** snapshot once per page → per card: scroll/visibility against the ORIGINAL element → re-query live DOM at the same selector → take `[index]` → all field reads bind to the fresh element.
**Invariant:** correctness requires BOTH lists to agree on position. Three distinct breakage classes, each costing exactly one all-NA row because :74 sits INSIDE the card-tier try (never a page abort): (1) LIVE-LIST SHRUNK (`len(live) <= index`, e.g. a card collapsed out mid-page) ⇒ `IndexError` at :74; (2) ORDER SHIFT (insertion/reorder) ⇒ SILENT WRONG-CARD EXTRACTION — fields read from the wrong person, the one failure class that produces plausible-but-wrong data rather than an NA row; (3) STALE ORIGINAL during :69/:72 (re-render between :133 and the loop body) ⇒ `StaleElementReferenceException` raised through `EC.visibility_of(item)`'s internal `_element_if_visible` before any retry exists (see stale-wait-boundary). The design trades duplicate queries for staleness immunity but keeps positional fragility as the residual risk.
**Probe:** no test files exist in the repo — source-grounded evidence only (coverage caveat). Observable boundaries (executed byte-exact): `grep -c 'find_elements' prospect_scraper_sales_navigator.py` = EXACTLY 2 (:74, :133); `grep -n 'scrollIntoView' ...` = :69 only; `grep -c 'TimeoutException\|StaleElementReference' ...` = 0 (no exception-type handling anywhere).
**Coverage caveat:** which class fires is runtime-DOM-dependent — the capsule pins the three classes and their costs, not their frequencies.

## Get live surrounding code
**Retrieve:** hyphenated selector tokens are BM25-invisible on this tiny graph (pass-3 recorded); symbol-anchored query instead:
```ts
await mcp.codebase_memory.search_graph({ project: "maximo3k-sales-nav-scraper", query: "scroll_extract enumerate items item", limit: 10, fields: ["signature", "name", "file"] });
```
→ resolves `scroll_extract` (`prospect_scraper_sales_navigator.py:57-122`) rank #1, carrying both :74 and the :59 enumerate source.

## Verdict
Adopt the snapshot-then-requery-at-same-index contract ONLY for pages whose card list is immutable during extraction; keep the per-card try so every mismatch costs one NA row, never the page. Adapt: if the host DOM reorders cards, replace positional matching with per-card identity anchors before porting. Omit the silent-wrong-card acceptance in any host where wrong data is worse than missing data. No-test caveat applies.
