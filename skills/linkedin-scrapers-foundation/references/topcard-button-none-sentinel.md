<!-- capsule-v2 -->
# Top-card button None sentinel — what does a scoped single-probe Easy Apply check actually classify, and where does its else-branch lie?

**Source:** EasyApplyJobsBot CC-BY-NC 4.0 `main@70fe7484ebe78646fc8e2dd2612459f37eed7a9f`; Codebase Memory `EasyApplyJobsBot`. **Question:** when the Easy Apply probe is scoped to the job's top card and returns `None`, which downstream outcomes does that absence really distinguish?

## Container-scoped probe → None → identity check — but the else-branch conflates three cases
**Path/Symbol:** `linkedin.py:Linkedin.easyApplyButton` (:358–366); sole consumer `linkJobApply` (:214–281, gate at :216).
**Signature:** `easyApplyButton(self) -> Optional[webdriver.remote.webelement.WebElement]`.
**Data Shape:** locator is ONE XPath whose outer predicate scopes to the top-card container class `jobs-apply-button--top-card`; jitter sleep runs BEFORE the probe; any exception (NoSuchElement included) collapses to `None`.

### Decisive source
```python
def easyApplyButton(self):
    try:
        time.sleep(random.uniform(1, constants.botSpeed))          # settle FIRST
        button = self.driver.find_element(By.XPATH,
            "//div[contains(@class,'jobs-apply-button--top-card')]//button[contains(@class,'jobs-apply-button')]")
        EasyApplyButton = button
    except Exception:
        EasyApplyButton = None                                     # absence = None sentinel
    return EasyApplyButton

# CONSUMER (linkJobApply :216/279-281):
if easyApplybutton is not None:          # identity check — correct form
    easyApplybutton.click(); ...
else:
    countAlreadyApplied += 1             # ⚠️ conflation:
    lineToWrite = jobProperties + " | " + "* 🥳 Already applied! Job: " + str(offerPage)
```

**Flow:** per job page: sleep jitter → one scoped find_element → element or None. The top-card container class does the scoping that LinkedIn-Easy-Apply-Bot achieves with a text filter over ALL `jobs-apply-button` matches; there is NO clickability wait and NO text verification here. Consumer branches on identity (`is not None`), clicks, walks the modal; on `None` it unconditionally books "🥳 Already applied!".
**Invariant:** the None sentinel is consumed by IDENTITY comparison (`is not None`, never truthiness) — keep that form in ports. But the classification it feeds is a LIE by construction: button-absence means already-applied OR external-only application OR a broken/slow page render, and this bot buckets all three into `countAlreadyApplied` feeding printSessionSummary's "Already applied" line. The sibling capsule easy-apply-button-sentinel shows the honest variant: False sentinel + attempted-column projection + page-source disambiguation ("You applied on" ⇒ already-applied). Also recorded: `constants.easyApplyButton` (:23, generic non-scoped XPath) is DEAD — grep finds zero usages of it/constants.totalJobs/constants.offersPerPage/constants.jobsPageCareerClass; inline literals drive behavior while the constants rot.
**Probe:** repo ships no tests (standing caveat). Executed byte-for-byte at HEAD: `grep -n "easyApplybutton is not None\|Already applied! Job\|countAlreadyApplied" linkedin.py` ⇒ exactly :132/:216/:279/:280/:297; `grep -n "constants.easyApplyButton\|constants.totalJobs\|constants.offersPerPage\|constants.jobsPageCareerClass" *.py` ⇒ zero usages (exit 1); graph trace_path(easyApplyButton, inbound) ⇒ callers_total 3 with linkJobApply the only hop-1 caller.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "EasyApplyJobsBot", query: "easyApplyButton", limit: 5 });
// ⇒ EasyApplyJobsBot.linkedin.Linkedin.easyApplyButton Method linkedin.py 358-366
await mcp.codebase_memory.trace_path({ project: "EasyApplyJobsBot", function_name: "easyApplyButton", direction: "inbound" });
```

## Verdict
Adopt the container-class scoping trick (one XPath predicate instead of post-filtering matches) and the identity-checked sentinel. Adapt by splitting the else-branch into real classifiers (page-source probes or badge checks) before trusting any "already applied" counter. Omit the dead selector constants pattern — if selectors live in constants, reference them; drift like this repo's is how stale locators survive code review. Contrast: easy-apply-button-sentinel owns the False-sentinel/honest-audit design; this capsule owns the scoped-probe/conflation-trap side.
