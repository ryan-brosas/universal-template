<!-- capsule-v2 -->
# Easy Apply modal driver — how do I walk a multi-step LinkedIn application form to submission without deadlocking on unknown questions?

**Source:** LinkedIn-Easy-Apply-Bot Apache-2.0 `master@8471c58b39e2a3bb3f4a2deb1e3c410e7fda7e0e` (`send_resume` :441–554); cross-checked against EasyApplyJobsBot CC-BY-NC `applyProcess` (:465–496) and Auto_job_applier_linkedIn MIT modal loop (:1008–1073). Codebase Memory `LinkedIn-Easy-Apply-Bot`. **Question:** what is the button-priority state machine inside the Easy Apply modal, and how does the error-recovery loop terminate?

## send_resume priority loop
**Path/Symbol:** `easyapplybot.py:EasyApplyBot.send_resume` (:441–554), locators table (:123–141), `fill_out_fields` (:417–427).
**Signature:** `send_resume() -> bool`; locators: `next="button[aria-label='Continue to next step']"`, `review="button[aria-label='Review your application']"`, `submit="button[aria-label='Submit application']"`, `error=".artdeco-inline-feedback__message"`.
**Data Shape:** modal state = whichever aria-label button is present; validation failures render `.artdeco-inline-feedback__message` nodes; success renders "application was sent" in page source.

### Decisive source
```python
while loop < 2:
    if is_present(upload_resume_locator):   resume_locator.send_keys(resume)   # uploads first, every pass
    elif len(self.get_elements("follow")) > 0: ...click()                       # follow-company checkbox
    if len(self.get_elements("submit")) > 0:
        ...click(); submitted = True; break                                     # 1. submit wins
    elif len(self.get_elements("error")) > 0:
        while len(elements) > 0:
            time.sleep(5)
            for element in elements: self.process_questions()                   # 2. fill & retry
            if "application was sent" in self.browser.page_source:
                submitted = True; break
            elif is_present(self.locator["easy_apply_button"]):
                submitted = False; break                                        # modal closed → give up cleanly
    elif len(self.get_elements("next")) > 0: ...click()                          # 3. advance step
    elif len(self.get_elements("review")) > 0: ...click()
```

**Flow:** upload → then each iteration checks submit > errors > next > review in strict priority → error loops re-run `process_questions` every 5 s until sent / modal-gone / bounded by outer `loop < 2`.
**Invariant:** check SUBMIT before NEXT — clicking Next when Submit is visible restarts the step and can loop forever; every click is gated by `EC.element_to_be_clickable` (30 s WebDriverWait); termination requires EITHER "application was sent" text OR the easy-apply button re-appearing — never an unbounded Next chain (Auto_job_applier additionally hard-caps at 15 Nexts).
**Probe:** repo has no test suite — coverage caveat recorded. Graph anchors: `LinkedIn-Easy-Apply-Bot.easyapplybot.EasyApplyBot.send_resume/process_questions/ans_question` all resolve.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "LinkedIn-Easy-Apply-Bot", query: "send_resume", limit: 5 });
```

## Verdict
Adopt the submit>error>next>review priority ladder with the two-way termination contract; adapt locator table (aria-labels are stable-ish but rot), wait budgets, and upload dict shape; omit the pyautogui manual-intervention prompts and the buggy `if "Yes" or "No" in answer` line (dead condition — porters must not copy it). Caveat: no upstream tests; behavior boundary is source-read only.
