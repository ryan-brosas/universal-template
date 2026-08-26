<!-- capsule-v2 -->
# Parent-anchor link extraction — the profile URL lives on the PARENT of the name span, not the span itself

**Source:** maximo3k-sales-nav-scraper (license file, `main@bdcd2e5197929f78631ab127d2fd10cee18807ca`); Codebase Memory `maximo3k-sales-nav-scraper`. **Question:** How does the scraper get a card's profile URL when no `data-anonymize` attribute carries it?

## XPath-parent hop from the name element
**Path/Symbol:** `prospect_scraper_sales_navigator.py:scroll_extract` :80–81.
**Signature:** `name_element.find_element(By.XPATH, "..")` → `link_element.get_attribute('href')`.
**Data Shape:** `name_element` is the `span[data-anonymize='person-name']` found at :77; its DOM parent is an `<a>` whose `href` is the profile URL. This is the ONLY field in the card not read from a `[data-anonymize=…]`-attributed element.

### Decisive source
```python
            name_element = item.find_element(By.CSS_SELECTOR, "span[data-anonymize='person-name']")
            person_name = name_element.text if name_element else "NA"

            link_element = name_element.find_element(By.XPATH, "..")
            person_link = link_element.get_attribute('href') if link_element else "NA"
```

**Flow:** find the name span → hop to its parent with the XPath axis `".."` → read `href` off that anchor.
**Invariant:** the URL's locator is STRUCTURAL (parent-of-name-span), not attributed — LinkedIn wraps each card's name in an anchor, so the parent hop is how the script recovers the one field Sales Navigator does not tag. Two traps for a porter: (1) this runs INSIDE the card-tier try, so a DOM change that unwraps the anchor routes the whole card to the NA row via failure-topology containment rather than yielding a row with an empty link; (2) the per-field `else "NA"` fallbacks are dead code here — `find_element` raises on absence, so only a successful pair of reads can produce a non-NA link.
**Probe:** no test files exist in the repo — source-grounded evidence only (coverage caveat). Observable boundary: the literal two-character XPath `".."` sits between the name-span find (:77) and the first attributed title read (:85).
**Coverage caveat:** anchors are re-derived against the CURRENT LinkedIn DOM at port time; the parent-hop MECHANISM is the portable contract, the exact wrapping is not.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "maximo3k-sales-nav-scraper", query: "scroll_extract data-anonymize scrollIntoView", limit: 10, fields: ["signature", "name", "file"] });
```
→ resolves the carrying function (`scroll_extract`, :57–122); the :80–81 hop is inside it.

## Verdict
Adopt the parent-axis hop as the pattern for harvesting un-attributed fields through an attributed neighbor: locate a tagged element, then navigate structurally (parent/child/sibling) to the untagged payload. Adapt which element is the anchor and which axis you hop. Omit nothing structural here — but re-verify the DOM wrapping on the live site before trusting any specific selector pair. No-test caveat applies.
