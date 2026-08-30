<!-- capsule-v2 -->
# Page-settle ladder — explicit sleeps stacked on top of every explicit wait

**Source:** maximo3k-sales-nav-scraper (license file, `main@bdcd2e5190792...` see Provenance `main@bdcd2e5197929f78631ab127d2fd10cee18807ca`); Codebase Memory `maximo3k-sales-nav-scraper`. **Question:** Where must a porter keep fixed delays even though Selenium waits are already present, and why do both exist?

## Wait-then-sleep at each phase boundary
**Path/Symbol:** `prospect_scraper_sales_navigator.py` — `scrape_results_page` (129–130), `scroll_extract` (72, 108), `login_to_site` (50–53), module scope (162).
**Signature:** pattern: `WebDriverWait(driver, 10).until(EC.presence_of_element_located(...))` followed by `time.sleep(N)`.
**Data Shape:** four distinct delay sites: (1) page level — 4 s after the `.artdeco-list` presence wait, BEFORE collecting cards; (2) card level — 1 s after appending an extracted row; (3) login level — 15 s after submit (security-check window); (4) shutdown level — 10 s before `driver.quit()`.

### Decisive source
```python
WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, ".artdeco-list")))
time.sleep(4)
li_elements_no_soup = driver.find_elements(By.CSS_SELECTOR, "li.artdeco-list__item.pl3.pv3")
```

**Flow:** every wait covers element EXISTENCE, not data COMPLETENESS — Sales Navigator renders list containers before populating cards and hydrates card content asynchronously, so the fixed sleeps cover the gap between "element present" and "data ready". The per-row 1 s sleep additionally throttles request rate to look less bot-like.
**Invariant:** presence ≠ ready. A porter who trusts the explicit waits alone collects zero-card pages or empty fields intermittently; the sleeps are load-bearing, not leftovers. Removing them changes behavior on slow connections even when all waits pass.
**Probe:** no test files exist in the repo — source-grounded evidence only (coverage caveat). Observable boundary: `time.sleep(4)` sits between the `.artdeco-list` wait and `find_elements`; the in-code usage comment (lines 17–18) instructs cancelling and fine-tuning the timers per Internet connection.
**Coverage caveat:** exact values (15/10/4/1 s) are tuned for one author's connection — treat as ratios to re-tune, not constants.

## Get live surrounding code
**Retrieve:** the sleep sites are bare statements without graph symbols; retrieve the functions carrying them.
```ts
await mcp.codebase_memory.search_graph({ project: "maximo3k-sales-nav-scraper", query: "page settle waits", limit: 10, fields: ["signature", "name", "file"] });
```
→ resolves `scrape_results_page` (:124-153, carries the 4 s site); `login_to_site` (:31-54) carries the 15 s site, `scroll_extract` (:57-122) the 1 s site.

## Verdict
Adopt the principle that explicit waits gate existence while fixed sleeps gate completeness/rate, applied at page-, card-, login- and shutdown-level boundaries. Adapt all four values to host network conditions — the in-code usage comment (:17–18) says to cancel the run and fine-tune the timers per connection. Omit nothing structural here — but never collapse the sleeps into the waits when porting. No-test caveat applies.
