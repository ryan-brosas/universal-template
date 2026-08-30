<!-- capsule-v2 -->
# Driver bootstrap — one Chrome session via webdriver-manager with no profile reuse

**Source:** maximo3k-sales-nav-scraper (license file, `main@bdcd2e5197929f78631ab127d2fd10cee18807ca`); Codebase Memory `maximo3k-sales-nav-scraper`. **Question:** How is the Chrome driver created and why does every run start from a logged-out browser?

## Module-level Chrome bootstrap
**Path/Symbol:** `prospect_scraper_sales_navigator.py` module scope (line 20; orchestration 155–164).
**Signature:** `driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()))` — module level, no options.
**Data Shape:** a single global `driver` consumed by both `login_to_site(driver, config)` and `scrape_results_page(driver)`; `ChromeDriverManager().install()` downloads/returns the matching chromedriver binary path at import/run time (network dependency).

### Decisive source
```python
driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()))
...
with open('config.json', 'r') as config_file:
    config = json.load(config_file)

login_to_site(driver, config)
scrape_results_page(driver)
time.sleep(10)
driver.quit()
```

**Flow:** create the Chrome instance first (before any login or page work) → load `config.json` → log in → scrape → sleep 10 s → quit. There is exactly one browser session for the whole run and it is never recreated mid-run.
**Invariant:** NO user-data-dir / profile options are set, so every run starts from a clean, logged-out session — the in-code comment states this is deliberate ("There are issues with Chrome profiles. Need to log in manually."). A porter who adds a persistent profile to "save the login" changes the contract this script was tuned around (stale cookies, profile lock conflicts) and must re-tune all waits.
**Probe:** no test files exist in the repo — source-grounded evidence only (coverage caveat). Observable boundary: `webdriver.Chrome(...)` is constructed with only a `service=` argument.
**Coverage caveat:** `config.json` holds placeholder values ("your email" / "your password" / "the link to your saved search") — it proves the three-key shape of the config contract, not working credentials.

## Get live surrounding code
**Retrieve:** the bootstrap itself is a module-level statement with no graph symbol; retrieve its first consumer instead.
```ts
await mcp.codebase_memory.search_graph({ project: "maximo3k-sales-nav-scraper", query: "login_to_site driver config", limit: 10, fields: ["signature", "name", "file"] });
```
→ resolves `login_to_site` (`prospect_scraper_sales_navigator.py:31-54`), whose `driver` parameter IS the module-level instance.

## Verdict
Adopt the single-session bootstrap pattern: webdriver-manager resolves the driver binary once at run start, and one explicit `quit()` closes the run. Adapt the browser choice/options to the host. Omit the hard-coded `prospects_1.csv` output path and the module-level (import-time side-effect) structure unless porting the script wholesale. No-test caveat applies.
