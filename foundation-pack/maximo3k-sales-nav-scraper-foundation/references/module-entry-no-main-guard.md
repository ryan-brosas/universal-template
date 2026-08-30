<!-- capsule-v2 -->
# No-main-guard entrypoint — importing the module launches Chrome and runs the whole scrape; quit() is best-effort

**Source:** maximo3k-sales-nav-scraper (GPL-3.0 license file) `main@bdcd2e5197929f78631ab127d2fd10cee18807ca`; Codebase Memory `maximo3k-sales-nav-scraper`. **Question:** Can this scraper be loaded as a library, and what actually guarantees the browser gets cleaned up?

## Flat top-level program with best-effort teardown
**Path/Symbol:** `prospect_scraper_sales_navigator.py` module scope — bootstrap `:20`, orchestration tail `:155-164`.
**Signature:** none — the program is flat top-level statements; `driver` exists at `:20` BEFORE the first `def` at `:22`.
**Data Shape:** fixed top-to-bottom execution: Chrome launch + network driver fetch (:20) → four defs (:22-153) → config parse (:155-156) → `login_to_site(driver, config)` (:159) → `scrape_results_page(driver)` (:160) → `time.sleep(10)` (:162) → `driver.quit()` (:164, last statement).

### Decisive source
```python
driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()))   # :20 — precedes every def

...four function definitions...

with open('config.json', 'r') as config_file:                                        # :155
    config = json.load(config_file)
login_to_site(driver, config)                                                        # :159
scrape_results_page(driver)                                                          # :160
time.sleep(10)                                                                       # :162
driver.quit()                                                                        # :164 — teardown ONLY on clean return
```

**Flow:** executing OR importing the file runs the entire pipeline — there is no `if __name__ == "__main__":` guard (`grep -c '__main__'` = 0). Because `scrape_results_page`'s unprotected `:129` wait (and every tier-C site) propagates straight out of module scope, `quit()` at :164 executes ONLY after a fully normal run; any mid-run crash abandons the Chrome window and chromedriver process with zero cleanup — there is no `finally` anywhere in the file (`grep -c 'finally'` = 0).
**Invariant:** import == run. Library reuse is impossible without restructuring: the module cannot be imported for its functions without paying the Chrome launch, the config read, and a full login+scrape. Teardown is a best-effort last statement, never a guaranteed one — the window-abandonment cost applies to EVERY tier-C crash (mid-run-authwall-death documents the one instance a page-level wait produces).
**Probe:** executed pre-write against the pin: `__main__ occurrences: 0`; `finally occurrences: 0`; order proof `:20` (driver line) precedes `:22` (first def); module tail printed byte-exact. Live graph evidence: `trace_path(login_to_site, inbound)` → callers_total 1, sole caller = the module scope itself.

## Get live surrounding code
**Retrieve:** the orchestration tail has no graph symbol; retrieve its callee to land on the boundary.
```ts
await mcp.codebase_memory.trace_path({ project: "maximo3k-sales-nav-scraper", function_name: "login_to_site", direction: "inbound", depth: 2 });
```
→ live-executed pre-write: callers_total 1 → `maximo3k-sales-nav-scraper.prospect_scraper_sales_navigator` (module hop), zero misses.

## Verdict
Adopt nothing structurally — this is the anti-pattern half of the leaf: wrap the ported pipeline in an explicit `main()` with `try/finally` (or context-manager) teardown so quit survives crashes. Adapt the entrypoint into a host CLI/library boundary with injected config and driver. Omit the import-side-effect structure entirely unless porting the script wholesale for one-shot manual use. No-test caveat applies.
