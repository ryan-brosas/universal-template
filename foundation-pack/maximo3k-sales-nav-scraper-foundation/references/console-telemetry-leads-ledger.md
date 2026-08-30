<!-- capsule-v2 -->
# Console telemetry leads the ledger — nine print sites are the ONLY progress channel, and stdout carries PII

**Source:** maximo3k-sales-nav-scraper (license file, `main@bdcd2e5197929f78631ab127d2fd10cee18807ca`); Codebase Memory `maximo3k-sales-nav-scraper`. **Question:** What observability does a porter get while the scraper runs, in what order does it fire relative to persistence, and what sensitive data lands in it?

## print-as-telemetry across all four phases
**Path/Symbol:** `prospect_scraper_sales_navigator.py` — 9 `print(` sites: :32 (login start), :70 (per-card scroll), :82 (profile link), :98 (name), :110 (card failure), :142 (next page), :144 (last page), :147 (no more pages), :150 (nav error).
**Signature:** bare built-in `print(...)` — no logging module anywhere in the file.
**Data Shape:** free-text lines mixing phase markers (`start login`, `Navigated to next page`), per-card progress (`Scrolled to item {index+1}`), and RAW EXTRACTED VALUES (`the person link is {person_link}` prints full profile URLs; `print(person_name)` prints each scraped name).

### Decisive source
```python
# order proof — the first telemetry line precedes ANY persistence capability:
def write_results_to_csv(results, filename):   # :22  defined
    ...
def login_to_site(driver, config):
    print('start login')                        # :32  FIRST runtime output
# inside scroll_extract's try, per card:
print(f"Scrolled to item {index + 1}")          # :70
link_element = name_element.find_element(By.XPATH, "..")
person_link = link_element.get_attribute('href')
print(f'the person link is {person_link}')      # :82  PII to stdout
...
results.append({...})                           # :99  row enters MEMORY only
time.sleep(1)
# ... rows reach the CSV only at :120, after ALL cards of the page
```

**Flow:** telemetry fires strictly BEFORE its corresponding state change everywhere: `Scrolled to item N` precedes the card's reads; the failure print (:110) precedes the all-NA append (:112); `Navigated to next page` (:142) follows the click but precedes the next page's extraction; the CSV write (:120) happens once per page while prints happen per card — so during a page, stdout is AHEAD of the ledger by up to one page of rows.
**Invariant:** stdout is the ONLY progress channel — the CSV is silent between pages and there is no logging, retry counter, or summary anywhere. Two consequences a porter must own: (1) crash forensics = last console line, which names the failing CARD INDEX (`Failed to process item at index {index}`) but pages already extracted sit in the CSV while the current page sits only in memory; (2) profile URLs and person NAMES go to stdout unconditionally (:82/:98) — redirecting console output shares PII as readily as sharing the CSV. There is no verbosity gate.
**Probe:** no test files exist in the repo — source-grounded evidence only (coverage caveat). Observable boundaries (all executed byte-exact against the pin): `grep -c 'print(' prospect_scraper_sales_navigator.py` = 9; `sed -n '57,122p' | grep -c 'print('` = 4; first-print-before-first-write proven by `grep -nE "print\('start login'\)|write_results_to_csv\(results"` = :32 vs :120 call site.
**Coverage caveat:** the count is 9 SITES not 9 distinct messages — :70 fires per card, so line volume scales with result count.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "maximo3k-sales-nav-scraper", query: "scroll_extract print", limit: 10, fields: ["signature", "name", "file"] });
```
→ resolves the carrying function (`scroll_extract`, :57-122, rank #1 among project symbols; `builtins.print` also surfaces as an unrelated node).

## Verdict
Adopt print-before-state-change telemetry ordering and per-index failure attribution as the debugging contract. Adapt: swap `print` for structured logging and REDACT the :82/:98 value dumps before any shared-console deployment. Omit nothing structural here — the ordering (telemetry leads persistence) is the portable behavior, not the print statements themselves. No-test caveat applies.
