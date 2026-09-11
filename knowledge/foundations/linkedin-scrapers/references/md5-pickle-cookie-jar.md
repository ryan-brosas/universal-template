<!-- capsule-v2 -->
# Hash-keyed pickle cookie jar — how does a Selenium bot restore a LinkedIn session across runs without scripting login every time?

**Source:** EasyApplyJobsBot CC BY-NC-SA 4.0 (learn-only: patterns + control flow, zero verbatim reuse) `main@70fe7484ebe78646fc8e2dd2612459f37eed7a9f`; Codebase Memory `EasyApplyJobsBot`. **Question:** where does the session jar live, when is it replayed vs rewritten, and what must a porter never break?

## Md5-keyed jar behind delete-before-replay restore
**Path/Symbol:** `linkedin.py:Linkedin.__init__` (:59–76), `getHash` (:78–79), `loadCookies` (:81–87), `saveCookies` (:89–104), `isLoggedIn` (:106–113).
**Signature:** `getHash(self, string: str) -> str`; `loadCookies(self) -> None`; `saveCookies(self) -> None`; `isLoggedIn(self) -> bool`.
**Data Shape:** jar path = `{cwd}/cookies/{md5(email)}.pkl`; value = pickled `driver.get_cookies()` list; key derived ONLY from the config email.

### Decisive source
```python
self.cookies_path = f"{os.path.join(os.getcwd(),'cookies')}/{self.getHash(config.email)}.pkl"
...
cookies = pickle.load(f)
self.driver.delete_all_cookies()
for cookie in cookies:
    self.driver.add_cookie(cookie)
...
except Exception as e:
    ...
    # Don't raise the exception - cookie saving is not critical for bot operation
```

**Flow:** launch driver (+optional stealth latch) → navigate `linkedin.com` → if the pickle exists: `delete_all_cookies()` THEN per-cookie `add_cookie` → liveness probe navigates `/feed`, returns True iff `//*[@id="ember14"]` resolves → on False, scripted email/password login → `saveCookies()` unconditionally afterwards (makedirs + `pickle.dump(get_cookies())`; every failure warned non-fatally).
**Invariant:** restore is DELETE-before-replay — a dirty live jar can never merge with the stored one; saving NEVER raises into the run (comment pins intent); account isolation comes free from md5(email) keying. TRAP 1: liveness selector `ember14` is a build-unstable GDS id — port "probe a stable feed marker", not this literal. TRAP 2: a FAILED login still falls through to `saveCookies()`, persisting the guest jar over the previous file.
**Probe:** `grep -n "delete_all_cookies\|add_cookie\|getHash(config.email)\|pickle.dump\|pickle.load" linkedin.py` ⇒ exactly :59/:84/:85/:87/:100 at HEAD — keying and restore order pinned.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "EasyApplyJobsBot", query: "loadCookies saveCookies isLoggedIn", limit: 10 });
await mcp.codebase_memory.get_code_snippet({ project: "EasyApplyJobsBot", qualified_name: "EasyApplyJobsBot.linkedin.Linkedin.loadCookies" });
```

## Verdict
Adopt: hash-of-account-keyed single-file pickle jar, delete-before-replay restore, non-fatal guarded save, navigate-then-probe liveness check. Adapt: replace ember14 with a stable marker or redirect probe (see `cookie-session-bootstrap`'s /login redirect-probe); gate save on login success. Omit: Windows-only `chromedriver.exe` join and the fixed 30s post-login sleep. Sibling jars: `cookie-session-persistence` (loud expiry), `sessions-json-cache` (username-keyed JSON), `pattern-filtered-cookie-jar` (regex-subset pickle) — this is the Selenium md5 variant. Coverage caveat: repo ships no tests; probe is source-grounded grep + graph snippet parity.
