<!-- capsule-v2 -->
# Easy-Apply button detection sentinel — how do I model "button absent" in a Selenium bot so downstream `attempted` bookkeeping can't silently lie?

**Source:** LinkedIn-Easy-Apply-Bot Apache-2.0 `master@8471c58b39e2a3bb3f4a2deb1e3c410e7fda7e0e`; Codebase Memory project `LinkedIn-Easy-Apply-Bot`. **Question:** what does the bot's `get_easy_apply_button → apply_to_job → write_to_file` chain actually do with the "no button" case, and why is the sentinel `False` rather than `None`?

## Text-filtered button search → False sentinel → `is not False` attempted flag

**Path/Symbol:** `easyapplybot.py:EasyApplyBot.get_easy_apply_button` (:396–415), consumer `apply_to_job` (:339, :344–351), audit projection `write_to_file` (:380 `attempted: bool = False if button == False else True`).
**Signature:** `get_easy_apply_button() -> WebElement | False` (deliberately NOT None); per candidate: text filter `"Easy Apply" in button.text` then `wait.until(EC.element_to_be_clickable(button))`; caller gate: `if button is not False:` (identity check).
**Data Shape:** locator `easy_apply_button` = XPath `'//button[contains(@class, "jobs-apply-button")]'` over ALL matches (not `.find_element` first-hit); sentinel value `False` doubles as the "external application / no easy apply" classifier; `write_to_file` row = `[timestamp, jobID, job, company, attempted, result]` where `attempted` derives from the SAME sentinel.

### Decisive source
```python
def get_easy_apply_button(self):
    EasyApplyButton = False                          # SENTINEL, not None
    try:
        buttons = self.get_elements("easy_apply_button")   # find_elements family
        for button in buttons:
            if "Easy Apply" in button.text:            # class alone is not enough:
                EasyApplyButton = button               # premium jobs reuse the class
                self.wait.until(EC.element_to_be_clickable(EasyApplyButton))
        except Exception as e:
            log.debug("Easy Apply button not found")   # swallow → False falls through
    return EasyApplyButton

# CONSUMER: identity comparison + audit projection
if button is not False:                    # 'is not', not truthiness
    …click/apply path…
self.write_to_file(button, jobID, self.browser.title, result)

def write_to_file(self, …):
    attempted: bool = False if button == False else True    # ledger column from sentinel
```

**Flow:** collect every `jobs-apply-button` match → keep the one whose visible text contains "Easy Apply" (class name alone also matches external-application buttons) → wait for clickability → return it, or `False` on zero matches/exception → `apply_to_job` branches on `button is not False`, else classifies via page-source probes ("You applied on" ⇒ already-applied) or reports no-easy-apply → the SAME object reaches `write_to_file`, where its non-False-ness IS the `attempted` audit column.
**Invariant:** the sentinel must be a single well-known value compared by IDENTITY (`is not False`): switching to `None` breaks nothing today but invites `if button:` truthiness ports where a stale/detached element would count as attempted; switching to exception-based absence loses the distinction between "no easy apply" and "page broke" that `write_to_file` records. The text filter is load-bearing — matching on class only makes premium "Apply" buttons clickable as if they were Easy Apply, submitting users to external flows. Every terminal branch assigns BOTH the outcome string and the result bool before the write (see string-outcome-channel); this capsule owns the OBJECT side of that contract.
**Probe:** repo ships no test suite — coverage caveat recorded. Deterministic probes verified at HEAD 8471c58: `grep -c "EasyApplyButton = False" easyapplybot.py` ⇒ 1 (single initialization site); `grep -n "button is not False\|button == False" easyapplybot.py` ⇒ exactly :339 and :380 (consumer gate + audit projection); graph anchor resolves: search_graph project `LinkedIn-Easy-Apply-Bot` query `get_easy_apply_button`.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "LinkedIn-Easy-Apply-Bot", query: "get_easy_apply_button", limit: 5 });
```

## Verdict
Adopt the triad: text-verified multi-match button selection, an explicit absence sentinel consumed by identity check, and deriving the audit `attempted` flag from that same sentinel so the ledger can never claim an attempt that didn't click. Adapt to Playwright by returning `null` AND using `=== null` strict equality — the invariant is single-sentinel identity semantics, not the literal `False`. Omit the bare-except swallow in new code (log-and-return-sentinel keeps the shape while surfacing breakage). Contrast: easy-apply-modal owns the IN-MODAL state machine after this seam hands off a verified-clickable button.
