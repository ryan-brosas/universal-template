<!-- capsule-v2 -->
# Chromedriver explicit-path relaunch — how do you survive webdriver-manager returning a binary Selenium cannot execute, without abandoning managed drivers?

**Source:** EasyApplyJobsBot CC-BY-NC 4.0 `main@70fe7484ebe78646fc8e2dd2612459f37eed7a9f`; Codebase Memory `EasyApplyJobsBot`. **Question:** when `ChromeDriverManager().install()` yields an unexecutable path (Windows WinError 193), what does the two-rung launch ladder actually fall back to?

## Repair the path explicitly; fallback re-runs the SAME manager
**Path/Symbol:** `linkedin.py:Linkedin.__init__` (:33–45); imports `ChromeDriverManager` (:19), `Service as ChromeService` (:20).
**Signature:** inline in `__init__`; rung 1 = explicit-path service, rung 2 = vanilla one-liner. No helper, no third rung.
**Data Shape:** warning is gated on `config.displayWarnings` and truncated to 50 chars (`str(e)[0:50]`); both rungs pass `options=utils.chromeBrowserOptions()`.

### Decisive source
```python
# Fix for WinError 193: Explicitly construct chromedriver path
try:
    chrome_install = ChromeDriverManager().install()
    folder = os.path.dirname(chrome_install)
    chromedriver_path = os.path.join(folder, "chromedriver.exe")   # REPAIR: rejoin dir + exe name
    service = ChromeService(chromedriver_path)
    self.driver = webdriver.Chrome(service=service, options=utils.chromeBrowserOptions())
except Exception as e:
    if config.displayWarnings:
        utils.prYellow(f"⚠️ Warning: Could not use explicit chromedriver path, using default: {str(e)[0:50]}")
    # Fallback to original method if explicit path fails
    self.driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()),
                                   options=utils.chromeBrowserOptions())   # SAME manager again
```

**Flow:** attempt 1 downloads/locates the driver via webdriver-manager, then rebuilds the executable path as `<install-dir>/chromedriver.exe` — because the manager can return a cache path whose final component is not the raw exe name Selenium tries to spawn (WinError 193 = "%1 is not a valid Win32 application"). If ANYTHING in rung 1 raises (download failure, network off, repair still wrong), rung 2 warns once and re-invokes the pre-fix vanilla expression — which calls the same manager with no repair.
**Invariant:** this is a REPAIR ladder, not a discovery ladder: both rungs depend on webdriver-manager succeeding, so "manager broken" kills the bot either way. The only guaranteed win is the path-shape fix (dir + known exe name). There is deliberately no PATH-lookup third rung — contrast path-first-browser-binary-discovery (LinkedIn-Easy-Apply-Bot), which resolves chromedriver/chrome via `shutil.which` FIRST and raises FileNotFoundError before any network code: opposite philosophy (discover-local vs download-managed). Handoff note: md5-pickle-cookie-jar cites this same __init__ for the session plane and its Verdict explicitly OMITS the "Windows-only chromedriver.exe join" — that deferred seam IS this capsule.
**Probe:** repo ships no tests (standing caveat). Executed byte-for-byte at HEAD: `grep -n "ChromeDriverManager\|ChromeService\|chromedriver.exe" linkedin.py` ⇒ exactly :19/:20/:35/:37/:38/:44; direct read of :29–76 matches the graph snippet byte-for-byte.
**Coverage:** check_index_coverage(linkedin.py) = no_recorded_issue + metadata_match @ gen 2026-08-23T00:13:12Z.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "EasyApplyJobsBot", query: "__init__ chromedriver ChromeService", limit: 5 });
// resolves Linkedin.__init__ (linkedin.py :29–76); snippet served matches checkout bytes
```

## Verdict
Adopt the explicit dir+exe rejoin as a cheap first rung whenever webdriver-manager's returned path shape is untrusted on Windows. Adapt: make rung 2 a genuinely different strategy (PATH lookup or pinned driver), not a re-run of the failing call. Omit the bare-except-with-truncated-message pattern in new code — catch WebDriverException specifically and log the full error. Caveat: behavior verified by source read only; no upstream test exercises either rung.
