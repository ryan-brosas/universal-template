<!-- capsule-v2 -->
# Integration skip gate + marker taxonomy — how does a test suite ship live-session tests that stay green offline without ever faking a pass?

**Source:** joeyism-linkedin-scraper GPL-3 `master@b1cdc1c0e85b…`; Codebase Memory `joeyism-linkedin-scraper`. **Question:** how do I split unit vs integration planes so missing credentials SKIP loudly instead of failing or lying?

## File-existence fixture gate + strict markers + documented rot skips
**Path/Symbol:** `tests/conftest.py:browser_with_session` (:40–53), `SESSION_FILE` (:16), `pytest_configure` marker registration (:98–103); `pytest.ini` (`asyncio_mode = auto`, `--strict-markers`, markers unit/integration/slow/e2e); rot documentation at `tests/test_job_scraper.py:11–13,33–35`.
**Signature:** `def browser_with_session()` pytest fixture (async usage); markers applied per test.
**Data Shape:** gate input = existence of `<repo root>/linkedin_session.json`; outcomes = yield loaded BrowserManager | `pytest.skip(reason)`.

### Decisive source
```python
@pytest.fixture
async def browser_with_session():
    if not SESSION_FILE.exists():
        pytest.skip("Session file not found. See README for session setup instructions.")
    async with BrowserManager(headless=False) as browser_manager:   # headed: LinkedIn blocks headless
        await browser_manager.load_session(str(SESSION_FILE))
        yield browser_manager

# selector rot is RECORDED, not hidden:
@pytest.mark.skip(reason="Job search selector '.jobs-search__results-list' not found - "
                         "LinkedIn page structure may have changed")
async def test_job_search_scraper(...):
```

**Flow:** collection → marker selection (`-m unit` / `-m integration`) → integration fixtures hit the file-existence gate → absent ⇒ skip WITH reason string; present ⇒ headed browser + session load. Unit plane stays headless=True against google/example so it runs anywhere.
**Invariant:** a missing session SKIPS (exit 0, visible `s`), never fails and never fabricates; strict-markers makes an unregistered marker a hard error so typos cannot silently untag live tests; known selector rot is an unconditional skip whose reason names the dead selector.
**Probe (executed at pinned HEAD):** `python3 -m pytest -m unit --no-header -q` → **7 passed, 15 deselected in 1.84s** (model dumps + browser manager context/navigation/session-save-load); `python3 -m pytest tests/test_company_scraper.py -m integration --no-header -q` with NO linkedin_session.json present → **3 skipped in 0.01s** (fixture-level skip, not failure). Runner note: required installing pytest+pytest-asyncio+playwright into the environment first — absence was recorded before install.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "joeyism-linkedin-scraper", query: "browser_with_session", limit: 5 });
// → tests.conftest.browser_with_session Function conftest.py :40–53
await mcp.codebase_memory.search_graph({ project: "joeyism-linkedin-scraper", query: "JobScraper scrape jobs", limit: 8 });
// → TESTS edges from tests/test_job_scraper.py into scrapers/job.py
```

## Verdict
Adopt the fixture-level existence gate + strict marker taxonomy + reason-carrying skips for any suite mixing offline units with credentialed live tests. Adapt the artifact path/marker names; keep the reason strings diagnostic ("which selector died"). Omit the dual registration belt-and-suspenders if you standardize on pytest.ini alone (conftest's addinivalue_line duplicates it minus e2e). Evidence: full runner GREEN observed; integration plane honestly skipped.
