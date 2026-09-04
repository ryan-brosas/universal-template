<!-- capsule-v2 -->
# Chrome profile degradation ladder — how do I reuse the user's real browser profile for login state, but never let a broken one kill the run?

**Source:** Auto_job_applier_linkedIn MIT `main@0ca5550`; Codebase Memory `Auto_job_applier_linkedIn`. **Question:** How should a Selenium/Chrome automation pick between the user's real profile, a guest/temp profile, and a retry — and what must be true before trusting the real profile?

## The ladder
**Path/Symbol:** `modules/open_chrome.py:createChromeSession` (:31–58); retry loop `:61+` catches `SessionNotCreatedException` and re-invokes with `isRetry=True`.
**Signature:** `createChromeSession(isRetry: bool = False) -> (options, driver, actions, wait)`.
**Data Shape:** inputs from config: `run_in_background` (`--headless`), `disable_extensions`, `safe_mode`, `auto_manage_driver` (undetected_chromedriver vs vanilla selenium import-time swap).

### Decisive source
```python
profile_dir = find_default_profile_directory()
if isRetry:
    print_lg("Will login with a guest profile, browsing history will not be saved in the browser!")
elif profile_dir and not safe_mode:
    options.add_argument(f"--user-data-dir={profile_dir}")
else:
    options.add_argument(f"--user-data-dir={get_default_temp_profile()}")
...
driver = uc.Chrome(options=options) if auto_manage_driver else webdriver.Chrome(options=options)
```

**Flow:** attempt 1 — if a default Chrome profile exists AND safe mode is off, attach to it (`--user-data-dir=<profile>`): LinkedIn session cookies come free from the user's real browsing. On `SessionNotCreatedException` (locked profile, version mismatch), the retry degrades to an isolated temp/guest profile and accepts a manual login. Headless and extension flags applied independently of profile choice; driver acquisition itself is dual-path (`undetected_chromedriver` when auto-managed).
**Invariant:** profile attachment is an OPTIMIZATION, never a requirement — every failure path lands on a working session (guest profile + manual login beats crash). The loud warning ("IF YOU HAVE MORE THAN 10 TABS OPENED...") documents the real failure mode of shared-profile attach. Contrast EasyApplyJobsBot's split `--user-data-dir=<parent> --profile-directory=<basename>` trick (browser-fingerprint-stealth): this repo attaches the whole discovered profile directory instead.
**Probe:** no direct test file pins createChromeSession (it spawns a real browser) — coverage caveat: behavior verified by source read at HEAD `0ca5550`; graph resolves the symbol directly.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "Auto_job_applier_linkedIn", query: "createChromeSession SessionNotCreatedException", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the three-rung ladder (real profile → temp profile → retry-with-guest) and the "session-at-all-costs" invariant. Adapt profile discovery to your OS. Omit the undetected_chromedriver import swap if your host manages drivers elsewhere.
