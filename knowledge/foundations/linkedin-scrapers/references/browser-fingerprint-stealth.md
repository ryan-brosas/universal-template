<!-- capsule-v2 -->
# Browser stealth & fingerprint — which automation tells does LinkedIn's stack catch, and what flags hide them?

**Source:** EasyApplyJobsBot CC-BY-NC `main@70fe7484ebe78646fc8e2dd2612459f37eed7a9f` (utils.chromeBrowserOptions + selenium-stealth), LinkedIn-Easy-Apply-Bot Apache-2.0 `master@8471c58b39e2a3bb3f4a2deb1e3c410e7fda7e0e` (:175–190), hassan-sales-nav-profiles-scraper NO-LICENSE `main@e294ac09c9b94bfcc8030079f31734bc9ae30dac` (`start_adspower_browser` :17–31, learn-only). Codebase Memory projects of the same names. **Question:** what concrete switches separate an automatable browser from a detectable one across Selenium and CDP-attach setups?

## Chrome options ladder + anti-detect attach
**Path/Symbol:** `utils.py:chromeBrowserOptions` (:14–49); `easyapplybot.py:EasyApplyBot.browser_options` (:175–190); `linkedin_scraper.py:start_adspower_browser` (:17–31); joeyism contrast: `core/browser.py:BrowserManager.__init__(headless, slow_mo, viewport, user_agent)` (:15–45).
**Signature:** returns a configured `webdriver.ChromeOptions`; profile branch splits any host path into `--user-data-dir=<parent>` + `--profile-directory=<basename>`, else `--incognito`.
**Data Shape:** the load-bearing pair is `--disable-blink-features=AutomationControlled` + `excludeSwitches:["enable-automation"]` + `useAutomationExtension:False` — together they suppress `navigator.webdriver` and the automation infobar.

### Decisive source
```python
options.add_argument("--disable-blink-features")
options.add_argument("--disable-blink-features=AutomationControlled")   # navigator.webdriver stays undefined
options.add_experimental_option('useAutomationExtension', False)
options.add_experimental_option("excludeSwitches", ["enable-automation"])
if len(config.chromeProfilePath) > 0:
    options.add_argument('--user-data-dir=' + initialPath)              # real-profile reuse beats cookies
    options.add_argument("--profile-directory=" + profileDir)

# Anti-detect external browsers expose a local WS endpoint instead:
ws_url = f"http://local.adspower.net:50325/api/v1/browser/start?user_id={user_id}"  # Bearer-keyed REST
browser = p.chromium.connect_over_cdp(ws_url["data"]["ws"]["puppeteer"])            # fingerprint lives in the PROFILE, not your code
```

**Flow:** build options → apply AutomationControlled suppression unconditionally → EITHER reuse a real Chrome profile (persistent fingerprint that matches history) OR run incognito → optionally layer selenium-stealth (languages/vendor/platform/webgl_vendor/renderer overrides, guarded by try/ImportError so missing dep degrades to plain options) → for hard targets, delegate the whole fingerprint to an anti-detect browser via CDP attach.
**Invariant:** headless is a per-config choice, never forced — both bots default headed because headless raises checkpoint rates; stealth wrapping must be failure-tolerant (missing package ≠ broken run).
**Probe:** no tests in EasyApplyJobsBot/LinkedIn-Easy-Apply-Bot/hassan repos — coverage caveat recorded; claims source-grounded at HEAD. joeyism pins lifecycle separately: `tests/test_browser.py::test_browser_manager_headless_mode`.
**License note:** hassan scraper has NO license — pattern recorded, zero code copied.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "EasyApplyJobsBot", query: "chromeBrowserOptions", limit: 10 });
await mcp.codebase_memory.search_graph({ project: "hassan-sales-nav-profiles-scraper", query: "start_adspower_browser", limit: 5 });
```

## Verdict
Adopt the three-flag AutomationControlled suppression and profile-reuse-over-cookies preference; adapt UA strings, stealth kwargs, and anti-detect vendor endpoints to host; omit pyautogui desktop hacks (see LinkedIn-Easy-Apply-Bot avoid_lock) and hard-coded AdsPower keys. Caveat: no direct tests pin any stealth behavior in these repos.
