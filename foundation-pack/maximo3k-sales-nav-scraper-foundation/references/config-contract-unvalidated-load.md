<!-- capsule-v2 -->
# Config contract — an unvalidated three-key `config.json` load whose missing keys crash tier C

**Source:** maximo3k-sales-nav-scraper (license file, `main@bdcd2e5197929f78631ab127d2fd10cee18807ca`); Codebase Memory `maximo3k-sales-nav-scraper`. **Question:** What is the exact shape of the configuration input, when is it read, what validates it, and what happens to a run whose config is malformed?

## Unvalidated three-key JSON load at module scope
**Path/Symbol:** `prospect_scraper_sales_navigator.py:155-156` (load) + consumers at :43/:44/:54.
**Signature:** `config = json.load(open('config.json', 'r'))` — no schema, no defaults, no key check.
**Data Shape:** flat JSON object with EXACTLY three string keys: `email`, `password`, `start_url`. The committed placeholder proves the shape: `{"email": "your email", "password": "your password", "start_url": "the link to your saved search"}` (with 2-space-indented closing brace and NO trailing newline). All three values are consumed verbatim by Selenium calls (`send_keys`, `driver.get`) — none is parsed further.

### Decisive source
```python
# :155-156 — module scope, AFTER the driver is constructed at :20
with open('config.json', 'r') as config_file:
    config = json.load(config_file)

login_to_site(driver, config)      # consumes config['email'], config['password']
scrape_results_page(driver)
```
```python
# login_to_site consumers:
email_field.send_keys(config['email'])        # :43
password_field.send_keys(config['password'])  # :44
...
    driver.get(config['start_url'])           # :54
```

**Flow:** construct Chrome FIRST (:20) → parse `config.json` from the CURRENT WORKING DIRECTORY (:155) → hand the dict to `login_to_site`, which reads `email`/`password` before submit and `start_url` only after the 15 s security-check window → `scrape_results_page` never touches config again.
**Invariant:** there are ZERO validation or default layers — three distinct failure classes all surface as uncaught tier-C crashes (see failure-topology): (1) file missing / invalid JSON ⇒ `FileNotFoundError`/`JSONDecodeError` at :156; (2) a MISSING key parses fine but raises `KeyError` LATER inside `login_to_site` (:43 first) — after Chrome has already launched, so the run dies with a browser window open; (3) a PLACEHOLDER value ("your email") passes every structural check and fails only at LinkedIn's form. The path is CWD-relative, so the script must be invoked from the repo root. The README adds a semantic constraint no code enforces: `start_url` must come from filtering a people search ("The tool is not made for already made lead lists", README:11) — lead-list URLs have a different DOM and break extraction silently.
**Probe:** no test files exist in the repo — source-grounded evidence only (coverage caveat). Observable boundary: `grep -n "open('config.json', 'r')" prospect_scraper_sales_navigator.py` = exactly line 155; `grep -c "except" <(sed -n '155,164p' ...)` = 0 (no handler around the load); `grep -nE "config\[" prospect_scraper_sales_navigator.py` = exactly :43/:44/:54.
**Coverage caveat:** the shipped `config.json` holds placeholders — it pins the three-key SHAPE, not working credentials.

## Get live surrounding code
**Retrieve:** the load is a bare module statement without a graph symbol; retrieve its consumer.
```ts
await mcp.codebase_memory.search_graph({ project: "maximo3k-sales-nav-scraper", query: "login_to_site config start_url", limit: 10, fields: ["signature", "name", "file"] });
```
→ resolves `login_to_site` (`prospect_scraper_sales_navigator.py:31-54`), the function holding all three `config[...]` reads.

## Verdict
Adopt the minimal three-key flat-config contract (credentials + start URL parsed once at run start, consumed raw). Adapt: resolve the config path absolutely and validate keys BEFORE constructing the driver if porting beyond the script's throwaway scope. Omit nothing structural here — but do not import this file's validation-free, CWD-relative loading into a long-lived service. No-test caveat applies.
