<!-- capsule-v2 -->
# PATH-first browser binary discovery — how do I make a Selenium launch deterministic on hosts where downloaded driver managers fail?

**Source:** LinkedIn-Easy-Apply-Bot Apache-2.0 `master@8471c58b39e2a3bb3f4a2deb1e3c410e7fda7e0e` (`EasyApplyBot.__init__` :101–112); repo context shell.nix / assets/chromedriver_* / .gitmodules; Codebase Memory `LinkedIn-Easy-Apply-Bot`. **Question:** how do you pin the browser + chromedriver pair at startup so the bot fails loudly BEFORE any network session instead of crashing mid-run on a version mismatch?

## shutil.which chain → FileNotFoundError → explicit Service wiring
**Path/Symbol:** `easyapplybot.py:EasyApplyBot.__init__` binary-resolution block (:101–112); flag assembly `browser_options` (:175–190); import aliasing :29–31.
**Signature:** no helper — inline in `__init__`: `shutil.which("chromedriver")`, `shutil.which("chromium") or shutil.which("google-chrome")`; raises `FileNotFoundError`; wires `ChromeService(chromedriver_path)` + `options.binary_location = chrome_path`.
**Data Shape:** both lookups return `str | None`; None ⇒ loud startup abort; the repo ALSO vendors `assets/chromedriver_{darwin,linux,windows}` binaries and a `shell.nix` dev-shell — three deployment strategies in one tree (vendored asset, nix profile, pip webdriver_manager submodule).

### Decisive source
```python
# Fix chromedriver on NixOS   (author comment :101)
chromedriver_path = shutil.which("chromedriver")
chrome_path = shutil.which("chromium") or shutil.which("google-chrome")

if not chromedriver_path:
    raise FileNotFoundError("Chromedriver not found in PATH.")
if not chrome_path:
    raise FileNotFoundError("Chromium/Chrome not found in PATH.")

self.options.binary_location = chrome_path
self.browser = webdriver.Chrome(service=ChromeService(chromedriver_path), options=self.options)
self.wait = WebDriverWait(self.browser, 30)
```

**Flow:** constructor time → resolve driver AND browser from PATH (chrome with chromium→google-chrome fallback) → missing either ⇒ FileNotFoundError BEFORE login/navigation begins → bind both explicitly (Service for the driver, binary_location for the browser) → only then start_linkedin.
**Invariant:** resolution failures are CONSTRUCTOR failures — a host without a matching stack can never reach network code or half-open a browser window; declaring BOTH binaries explicitly removes the silent download-and-hope path of webdriver_manager (kept here only as an unused gitmodule/pip dependency). This matters most on immutable/NixOS-style hosts where post-launch downloads land in non-writable paths.
**Probe:** repo ships no test suite — coverage caveat recorded. Deterministic probes verified byte-for-byte at HEAD 8471c58: `grep -n "shutil.which\|binary_location\|FileNotFoundError\|ChromeService" easyapplybot.py` ⇒ :29/:103/:104/:107/:109/:111/:112 (exactly one resolution block); `git ls-files` confirms assets/chromedriver_linux + darwin + windows vendored and .gitmodules present while the webdriver_manager worktree dir is EMPTY locally (uninitialized submodule — pip package supplies the import).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "LinkedIn-Easy-Apply-Bot", query: "browser chromedriver options chrome", limit: 5 });
// ⇒ EasyApplyBot.browser_options :175-190 (resolved live this pass; resolution block sits in __init__ :101-112)
```

## Verdict
Adopt PATH-first discovery with fail-fast constructor errors and explicit dual binding whenever your host manages browsers via system packages (NixOS, CI images, distro chrome); adapt the fallback chain to local browser names (edge/chrome variants) and consider asserting driver/browser major versions match; omit reliance on the uninitialized webdriver_manager submodule and the vendored assets/ binaries (they rot against modern Chrome majors). Contrast: puppeteer-flag-stack owns LAUNCH FLAGS; this seam owns finding WHAT to launch. Caveat: source-read only.
