<!-- capsule-v2 -->
# Progress-percent step budget — how many fill→Continue clicks does a multi-step Easy Apply form need before Review/Submit?

**Source:** EasyApplyJobsBot CC BY-NC-SA 4.0 (learn-only: patterns + control flow, zero verbatim reuse) `main@70fe7484ebe78646fc8e2dd2612459f37eed7a9f`; Codebase Memory `EasyApplyJobsBot`. **Question:** when the modal reports its own completion percentage, how is that metric turned into a safe walk budget?

## Computed budget floor(100/perc)-2 with negative-range no-op safety
**Path/Symbol:** `linkedin.py:Linkedin.applyProcess` (:465–496); percentage read in `linkJobApply` exception island (:250–262); issue-#72 interstitial dismiss (:220–228).
**Signature:** `applyProcess(self, percentage: int, offerPage: str) -> str`.
**Data Shape:** percentage parsed from the modal progress span text (e.g. "33%"); budget = `math.floor(100 / percentage) - 2`.

### Decisive source
```python
applyPages = math.floor(100 / percentage) - 2
result = ""
for pages in range(applyPages):
    self.fillPhoneNumber()
    self.driver.find_element(By.CSS_SELECTOR, "button[aria-label='Continue to next step']").click()
    time.sleep(random.uniform(1, constants.botSpeed))
...
if config.dryRun:
    result = "* 🧪 DRY RUN - Would apply to this job: " + str(offerPage)
    return result
...  # Review your application → optional follow-company uncheck → Submit application
```

**Flow:** single-step submit attempt fails ⇒ the exception island reads completion % off the progress span ⇒ computes the budget ⇒ runs exactly that many phone-fill + Continue clicks ⇒ dry-run gate placed AFTER all form mutation but BEFORE Review/Submit (the irreversible boundary) ⇒ Review → optional follow-company checkbox uncheck → Submit. Interstitial: right after opening Easy Apply, one displayed "Continue to next step" button is dismissed once (:220–228).
**Invariant:** stepping is METRIC-driven, not button-probing (contrast `easy-apply-modal`'s submit>error>next>review priority machine). Executed values: p=100→-1, 66→-1, 50→0, 33→1, 25→2 — a ≤0 budget makes `range()` a SAFE NO-OP, so over-reported percentages can never over-click; the "-2" reserves the Review and Submit clicks outside the loop. Under-reported % clicks a missing button ⇒ NoSuchElement bubbles to the cannot-apply island; percentage==0 raises ZeroDivisionError in applyProcess, caught by the same island. Damage is bounded either way.
**Probe:** `python3 -c "import math; print([(p, math.floor(100/p)-2) for p in (100,66,50,33,25)])"` ⇒ `[(100, -1), (66, -1), (50, 0), (33, 1), (25, 2)]`; `grep -n "floor(100" linkedin.py` ⇒ :466.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "EasyApplyJobsBot", query: "applyProcess applyPages progress", limit: 10 });
await mcp.codebase_memory.get_code_snippet({ project: "EasyApplyJobsBot", qualified_name: "EasyApplyJobsBot.linkedin.Linkedin.applyProcess" });
```

## Verdict
Adopt: computed metric-driven stepping, dry-run-before-submit placement, one-shot interstitial dismissal. Adapt: the -2 constant to the host's review/submit structure; guard division by zero explicitly instead of relying on the outer island. Omit: nothing structural. Coverage caveat: no upstream tests; formula executed directly + grep pin + graph parity.