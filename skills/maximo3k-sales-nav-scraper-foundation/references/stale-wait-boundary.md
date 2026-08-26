<!-- capsule-v2 -->
# Stale-wait boundary — the visibility wait itself raises StaleElementReferenceException before the re-find can heal

**Source:** maximo3k-sales-nav-scraper (license file, `main@bdcd2e5197929f78631ab127d2fd10cee18807ca`); Codebase Memory `maximo3k-sales-nav-scraper`. **Question:** Where exactly does the stale-element countermeasure NOT cover, and which statement still throws on a stale element despite it?

## The :72 wait runs against the ORIGINAL element
**Path/Symbol:** `prospect_scraper_sales_navigator.py:scroll_extract` :69-74.
**Signature:** `WebDriverWait(driver, 10).until(EC.visibility_of(item))` — `item` is the caller's ORIGINAL element reference; `EC.visibility_of` wraps `_element_if_visible`, whose first act is `element.is_displayed()` — an immediate wire call that RAISES `StaleElementReferenceException` for a dead reference.
**Data Shape:** two element references exist per card: the original (from the caller's snapshot) used by :69/:72, and the re-found replacement (:74) used by all field reads. The heal at :74 cannot apply to :72 because the exception fires INSIDE `until()`'s predicate invocation.

### Decisive source
```python
driver.execute_script("arguments[0].scrollIntoView(true);", item)      # :69 original
WebDriverWait(driver, 10).until(EC.visibility_of(item))                # :72 original — can raise STALE here
item = driver.find_elements(By.CSS_SELECTOR, "li.artdeco-list__item.pl3.pv3")[index]  # :74 fresh — heals AFTER
```

**Flow:** per card: scroll original → visibility-wait original → RE-FRESH binding → read fields. If LinkedIn re-rendered the list between the caller's :133 snapshot and this iteration's :69/:72, :72 (or :69's script execution) throws `StaleElementReferenceException`; the card-tier except (:109) converts it into the standard all-NA row + continue. The stale-safety story therefore has TWO layers with different coverage: the re-find (:74) makes FIELD READS immune, but the scroll/wait prologue (:69/:72) remains exposed by design — no retry, no `ignored_exceptions` configuration (`grep -c ignore` = 0; `until()` does not retry StaleElementReferenceException anyway because Selenium treats staleness as non-transient for predicates).
**Invariant:** the countermeasure covers reads-after-refresh, not existence-before-refresh. A porter who believes "the re-find handles staleness" and deletes the per-card try will crash whole pages on the FIRST mid-page re-render; conversely, moving the re-find ABOVE the wait would trade a caught exception for a wrong-card or IndexError hazard (see index-coupling-failure-modes). The exact containment cost is one NA row per stale prologue.
**Probe:** no test files exist in the repo — source-grounded evidence only (coverage caveat). Observable boundaries (executed byte-exact): `sed -n '57,122p' | grep -nE 'visibility_of\(item\)|find_elements\(By.CSS_SELECTOR'` = relative :16 (abs :72) BEFORE relative :18 (abs :74); `grep -c 'TimeoutException\|StaleElementReference\|ignore' prospect_scraper_sales_navigator.py` = 0.
**Coverage caveat:** Selenium-version behavior of `visibility_of` internals is environmental; the in-source facts are the ORDERING (:72 precedes :74) and the absence of any retry/stale handling.

## Get live surrounding code
**Retrieve:** selector tokens are BM25-invisible here; symbol-anchored query:
```ts
await mcp.codebase_memory.search_graph({ project: "maximo3k-sales-nav-scraper", query: "scroll_extract StaleElementReferenceException re-find", limit: 10, fields: ["signature", "name", "file"] });
```
→ resolves `scroll_extract` (`prospect_scraper_sales_navigator.py:57-122`) rank #1.

## Verdict
Adopt the layered reading: re-find protects field reads; the pre-refind prologue stays exposed and leans on the card-tier try as its only net. Adapt: if the host needs zero-NA extraction under re-renders, wrap :69/:72 in their own bounded stale-retry BEFORE porting the loop. Omit the claim "staleness handled" from any consumer summary — the precise contract is "staleness contained to one NA row". No-test caveat applies.
