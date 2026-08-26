<!-- capsule-v2 -->
# Login flow — authenticate through a possible captcha and land on the saved-search URL

**Source:** maximo3k-sales-nav-scraper (license file, `main@bdcd2e5197929f78631ab127d2fd10cee18807ca`); Codebase Memory `maximo3k-sales-nav-scraper`. **Question:** How does the script authenticate to LinkedIn and reach the saved-search start URL when LinkedIn may interpose a security check after submit?

## Manual-captcha login handoff
**Path/Symbol:** `prospect_scraper_sales_navigator.py:login_to_site` (lines 31–54).
**Signature:** `def login_to_site(driver, config)`.
**Data Shape:** takes the live Selenium `driver` and the parsed `config` dict (`email`, `password`, `start_url` string keys); mutates the driver's current page from the LinkedIn login form to `config['start_url']`.

### Decisive source
```python
driver.get("https://www.linkedin.com/login")
WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.NAME, "session_key")))
email_field = driver.find_element(By.NAME, "session_key")
password_field = driver.find_element(By.NAME, "session_password")
email_field.send_keys(config['email'])
password_field.send_keys(config['password'])
password_field.send_keys(Keys.RETURN)
# if there is a security check
time.sleep(15)
WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
driver.get(config['start_url'])
```

**Flow:** open `/login` → wait until the `session_key` input exists → type credentials from config → submit with `Keys.RETURN` → blind-fixed 15 s window for a human to solve any security check → wait for `<body>` presence → navigate to the saved-search `start_url`.
**Invariant:** the script never detects, classifies, or solves a challenge — after submit it waits a FIXED window and proceeds unconditionally; the `start_url` navigation happens *after* that window so a solved challenge (which redirects to the feed) is overridden by the explicit saved-search navigation. A porter who removes the fixed window breaks runs whenever LinkedIn challenges the login; a porter who adds challenge detection is building beyond this contract.
**Probe:** no test files exist in the repo — source-grounded evidence only (coverage caveat). Observable boundary: `time.sleep(15)` sits between `Keys.RETURN` and the next wait, unconditional.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "maximo3k-sales-nav-scraper", query: "login_to_site session_key session_password RETURN", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the credential-fill → submit → fixed security-window → explicit start-url navigation sequence, with field locators by NAME (`session_key`/`session_password`). Adapt the 15 s window size, the login URL, and the field names to the host target. Omit any automated challenge solving — this contract deliberately hands control to a human. No-test caveat applies.
