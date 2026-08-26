<!-- capsule-v2 -->
# Chrome profile path split normalization — how does one cross-platform profile path string become Chrome's two-argument profile attach without breaking on mixed separators?

**Source:** EasyApplyJobsBot CC-BY-NC 4.0 `main@70fe7484ebe78646fc8e2dd2612459f37eed7a9f`; Codebase Memory `EasyApplyJobsBot`. **Question:** given `--user-data-dir=<parent>` + `--profile-directory=<basename>` as the only attach form, what must happen to a raw config path — and what does the no-separator fallback actually produce?

## Normalize both separators → rfind split → degenerate branch emits an EMPTY user-data-dir
**Path/Symbol:** `utils.py:chromeBrowserOptions` (:14–49; profile tail :28–48).
**Signature:** `chromeBrowserOptions() -> webdriver.ChromeOptions` (no args; reads `config.chromeProfilePath`, `config.headless`).
**Data Shape:** non-profile path ⇒ `--incognito`; profile path ⇒ exactly two arguments: `'--user-data-dir=' + initialPath` and `"--profile-directory=" + profileDir`.

### Decisive source
```python
if len(config.chromeProfilePath) > 0:
    # Normalize path separators to handle mixed separators
    normalized_path = config.chromeProfilePath.replace('\\', os.sep).replace('/', os.sep)
    last_sep_index = normalized_path.rfind(os.sep)
    if last_sep_index != -1:
        initialPath = normalized_path[:last_sep_index]            # parent → user-data-dir
        profileDir  = normalized_path[last_sep_index + 1:]        # basename → profile-directory
    else:
        # "treat entire path as profile directory"
        initialPath = os.path.dirname(normalized_path)            # dirname('BareName') == ''
        profileDir  = os.path.basename(normalized_path)
    options.add_argument('--user-data-dir=' + initialPath)
    options.add_argument("--profile-directory=" + profileDir)
else:
    options.add_argument("--incognito")
```

**Flow:** flag floor first (`--no-sandbox --ignore-certificate-errors --disable-extensions --disable-gpu --disable-dev-shm-usage`, conditional `--headless`, always `--start-maximized`, then the AutomationControlled trio owned by browser-fingerprint-stealth) → if a profile path is configured, normalize BOTH separator styles onto `os.sep`, split at the LAST separator, and emit the parent/basename pair.
**Invariant:** executed behavior table (exact source expressions, this pass): `'C:\Users\u\Profile'` → (`C:/Users/u`, `Profile`); `'/home/u/chrome-profile/Default Profile'` → (`/home/u/chrome-profile`, `Default Profile`); **`'BareName'` → (`''`, `BareName`) — an EMPTY `--user-data-dir=` argument**, because `os.path.dirname` of a bare name is the empty string. The in-code comment ("use parent directory as user-data-dir") promises something the code cannot deliver on that branch. Ports must either reject bare names or resolve them against a real base dir. Ownership boundaries: this capsule owns path NORMALIZATION; browser-fingerprint-stealth owns the detection flags sharing this function; chrome-profile-degradation-ladder (Auto_job_applier) owns profile DISCOVERY plus guest/temp fallback — different questions entirely.
**Probe:** repo ships no tests (standing caveat). Executed byte-for-byte at HEAD: `grep -n "rfind(os.sep)\|profile-directory" utils.py` ⇒ :34/:46; live-exec of the exact expressions printed the three-row table above (bare name ⇒ empty string confirmed). Direct read :14–73 matches graph snippet byte-for-byte.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "EasyApplyJobsBot", query: "chromeBrowserOptions profile directory user-data-dir", limit: 5 });
// ⇒ EasyApplyJobsBot.utils.chromeBrowserOptions Function utils.py 14-49
```

## Verdict
Adopt the both-separators-normalize-then-rfind split for any host-supplied Chrome profile path. Adapt by validating the basename branch: empty `user-data-dir` silently launches with a default/odd store. Omit the hard-coded `.exe` assumptions elsewhere in this repo (see chromedriver-explicit-path-relaunch); keep profile attach and driver resolution as separate concerns. Caveat: source-read + expression-exec evidence only; launching real Chrome per row would need a display environment.
