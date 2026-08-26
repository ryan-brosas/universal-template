<!-- capsule-v2 -->
# Mid-run authwall death — the page-level presence wait sits OUTSIDE every try tier

**Source:** maximo3k-sales-nav-scraper (license file, `main@bdcd2e5197929f78631ab127d2fd10cee18807ca`); Codebase Memory `maximo3k-sales-nav-scraper`. **Question:** What happens to the pagination loop when LinkedIn interposes a session/auth wall AFTER login succeeded?

## Unprotected artdeco-list wait at loop top
**Path/Symbol:** `prospect_scraper_sales_navigator.py:scrape_results_page` :129.
**Signature:** `WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, ".artdeco-list")))` — first statement of every `while True:` iteration, no surrounding try.
**Data Shape:** waits up to 10 s for the results-list container; raises `TimeoutException` on absence. The only try tiers in the call path are INSIDE `scroll_extract` (card tier) and BELOW :129 (pagination button tier) — neither wraps this statement.

### Decisive source
```python
while True:  # Loop through all pages
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, ".artdeco-list")))  # :129 UNPROTECTED
    time.sleep(4)
    li_elements_no_soup = driver.find_elements(By.CSS_SELECTOR, "li.artdeco-list__item.pl3.pv3")          # :133
    scroll_extract(driver, li_elements_no_soup)
    try:                                                                                                   # :138 — first handler,
        next_button = driver.find_element(...)                                                              #        and it is BELOW
```

**Flow:** click Next → new page loads → :129 demands `.artdeco-list` within 10 s → on timeout the exception unwinds `scrape_results_page`, then module scope (:160, no handler) → process exits → the final `time.sleep(10)` + `driver.quit()` (:162-163) NEVER RUN — the Chrome window is left open on the authwall.
**Invariant:** the scraper has NO mid-run session-loss recovery: an authwall (or any redesign removing the container) kills the whole run from ANY page ≥ 1, even though every earlier page's rows are already committed (page-commit-unit durability). This is the deliberate complement of the login-time 15 s human handoff — that window covers challenges only at AUTH TIME; there is no second handoff mid-run. A porter who adds re-auth here must also decide what the already-written ledger rows mean for the resumed run (the append-only CSV will duplicate them).
**Probe:** no test files exist in the repo — source-grounded evidence only (coverage caveat). Observable boundaries (executed byte-exact): `grep -n 'artdeco-list"' prospect_scraper_sales_navigator.py` = :129 only; the first `try` of the function appears at :138, strictly after :129; `sed -n '155,164p' | grep -c except` = 0 (module scope handler-free).
**Coverage caveat:** TimeoutException is the canonical trigger; ANY exception from :129 (including WebDriver death) propagates identically since nothing catches it.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "maximo3k-sales-nav-scraper", query: "scrape_results_page pagination next", limit: 10, fields: ["signature", "name", "file"] });
```
→ resolves `scrape_results_page` (`prospect_scraper_sales_navigator.py:124-153`), whose :129 statement this capsule owns.

## Verdict
Adopt as the explicit boundary of the fault-tolerance envelope: card errors degrade, navigation-button errors stop cleanly, but anything failing BEFORE the button check — above all the unprotected :129 wait — crashes the run un-gracefully (window left open). Adapt: wrap :129 with an explicit authwall detector + bounded re-login if the host needs survivable long runs. Omit any assumption of mid-run session healing when reusing the other capsules' containment guarantees. No-test caveat applies.
