<!-- capsule-v2 -->
# Lookup exception topology — which exception does each Selenium lookup actually raise, and what happens to error handling that names the wrong one?

**Source:** LinkedIn-Easy-Apply-Bot Apache-2.0 `master@8471c58b39e2a3bb3f4a2deb1e3c410e7fda7e0e` (`start_linkedin` :192–216 dead catch :213–216; `is_present`/`get_elements` :430–439; explicit-wait construction :114; `browser_options` :175–190; `requirements.txt:1`); Codebase Memory `LinkedIn-Easy-Apply-Bot`. **Question:** how must a porter match exception types to Selenium's three lookup APIs so a designed soft-fail doesn't silently become a crash?

## Three lookup APIs, three exception contracts — one except clause that names none of them

**Path/Symbol:** `easyapplybot.py:EasyApplyBot.start_linkedin` (:192–216), `EasyApplyBot.is_present` (:437–439), `EasyApplyBot.get_elements` (:430–435), `self.wait = WebDriverWait(self.browser, 30)` (:114).
**Signature:** `is_present(locator) -> bool`; `get_elements(type) -> list`; `start_linkedin(username, password) -> None`.
**Data Shape:** `locator` entries are `(By, selector)` tuples from the table at :123–141; `find_elements` returns `[]` on absence; plain `find_element` raises; `WebDriverWait(...).until(...)` raises `TimeoutException`.

### Decisive source
```python
# start_linkedin :196–216 — PLAIN find_element under an except TimeoutException
try:
    user_field = self.browser.find_element("id","username")
    pw_field = self.browser.find_element("id","password")
    login_button = self.browser.find_element(By.CSS_SELECTOR, 'button[type="submit"]')
    ...
except TimeoutException:
    log.info("TimeoutException! Username/password field or login button not found")

# the repo's OWN total idiom elsewhere (:437–439) — find_elements NEVER raises:
def is_present(self, locator):
    return len(self.browser.find_elements(locator[0], locator[1])) > 0

# :114 — the only wait object is EXPLICIT; nothing configures implicit waits
self.wait = WebDriverWait(self.browser, 30)
```

**Flow:** constructor builds one explicit-wait object (:114) → login navigates and looks up fields with **plain `find_element`** → if a field is missing, Selenium raises `NoSuchElementException` (with or without an implicit wait — implicit waits still raise `NoSuchElementException` after polling) → `except TimeoutException` cannot catch it → the exception propagates out of `start_linkedin` through `__init__` :117 and crashes `EasyApplyBot(...)` construction in `__main__`, despite the log line promising a graceful continue. Everywhere else the repo follows the never-raise idiom: `is_present` (4 call sites: applications_loop, get_elements, process_questions, send_resume) probes `len(find_elements(...)) > 0`, and `get_elements` returns `[]` unless present.
**Invariant:** exception TYPE must track lookup API. `find_elements` never raises (totality is why len-probes work). Plain `find_element` raises `NoSuchElementException`. Only `WebDriverWait.until` raises `TimeoutException` — whose default `ignored_exceptions` is precisely `(NoSuchElementException,)`. An except clause naming the wrong class is dead code that converts a designed soft-fail into an unhandled crash; here the repo configured NO implicit wait anywhere (zero `implicitly_wait` sites repo-wide), so there was not even a version where the catch could fire.
**Probe:** repo ships no test suite — coverage caveat recorded. Executed byte-for-byte at HEAD 8471c58: `grep -n "implicitly_wait\|WebDriverWait" easyapplybot.py` ⇒ exactly :27 (import) and :114 (explicit-wait construction) — zero implicit-wait configuration sites; `requirements.txt:1` pins bare `selenium` (unversioned ⇒ modern 3.x/4.x semantics govern). Live-WebDriver behavioral probe BLOCKED by environment (selenium not importable anywhere in permitted envs; installing would exceed the lane file boundary) — semantics doc-verified instead: [selenium.common.exceptions](https://www.selenium.dev/selenium/docs/api/py/selenium_common/selenium.common.exceptions.html) ("NoSuchElementException … Thrown when element could not be found"), [WebDriverWait API](https://www.selenium.dev/selenium/docs/api/py/selenium_webdriver_support/selenium.webdriver.support.wait.html) (TimeoutException raised by `until` expiry; default ignored_exceptions = NoSuchElementException only), [implicit-vs-explicit wait table](https://www.baeldung.com/selenium-implicit-explicit-wait).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "LinkedIn-Easy-Apply-Bot", query: "start_linkedin login username password timeout", limit: 5 });
// ⇒ EasyApplyBot.start_linkedin :192-216 (BM25 rank 1, executed this pass)
await mcp.codebase_memory.search_graph({ project: "LinkedIn-Easy-Apply-Bot", query: "get_elements is_present find_elements presence probe", limit: 5 });
// ⇒ get_elements :430-435 + is_present :437-439 (executed)
await mcp.codebase_memory.trace_path({ project: "LinkedIn-Easy-Apply-Bot", function_name: "is_present", direction: "inbound", depth: 1 });
// ⇒ 4 callers: applications_loop, get_elements, process_questions, send_resume (executed)
```

## Verdict
Adopt the totality discipline: probe presence with `len(find_elements(...)) > 0`, collect with find-elements-and-filter, and reserve `TimeoutException` handling exclusively for explicit-wait blocks. Adapt missing-element handling around plain `find_element` to catch `NoSuchElementException` or convert the lookup into an explicit wait before writing any soft-fail branch — richer suite twins for the wait side: playwright-resilient-helpers (severity-split waits) and text-find-best-match-ladder (find-as-wait that raises TimeoutError contractually). Omit this repo's fixed-sleep login pacing and its commented-out 2FA block (:209–215), and do not port the dead catch itself. Contrast: easy-apply-button-sentinel shows the same repo doing it right — absence flows as a returned sentinel value, not as a caught (wrong) exception.
