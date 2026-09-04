<!-- capsule-v2 -->
# Stuck-modal-loop breaker — how do I bound an unpredictable multi-page application form and hand control to a human without abandoning the run?

**Source:** Auto_job_applier_linkedIn MIT `main@0ca5550f8aa80027621cfc17a30fceba05705f84`; Codebase Memory `Auto_job_applier_linkedIn`. **Question:** Easy Apply modals can loop Next forever on unseen question types — what bounded counter + outcome vocabulary turns an infinite UI loop into either a human takeover or a clean discard?

## next_counter bound, errored vocabulary, and finally-block submit policy
**Path/Symbol:** `runAiBot.py:apply_to_jobs` inner Easy Apply block (:1008–1073) — counter latch :1018–1031; `errored` vocabulary "" / "nose" / "stuck" (:1011, :1029–1030, :1040); finally-block submit policy :1041–1063; failure island :1066–1073.
**Signature:** local state inside the per-job try: `next_counter`, `errored`, `questions_list`, `cur_pause_before_submit`.
**Data Shape:** `questions_list` set of (label, answer, type, prev_answer) audit tuples; screenshots named "{job_id} - {failedAt} - {timestamp}.png".

### Decisive source
```python
next_counter = 0
while next_button:
    next_counter += 1
    if next_counter >= 15:
        if pause_at_failed_question:                     # human-takeover path RESETS the latch
            screenshot(driver, job_id, "Needed manual intervention for failed question")
            pyautogui.alert("...DO NOT CLICK Back, Next or Review...", "Help Needed", "Continue")
            next_counter = 1; continue                   # human answered it → keep going
        ...raise Exception("Seems like stuck in a continuous loop of next...")
    questions_list = answer_questions(modal, questions_list, work_location, job_description=description)
    ...
except NoSuchElementException: errored = "nose"          # structured miss ≠ generic failure
finally:
    if errored != "stuck" and cur_pause_before_submit:   # never pause on a poisoned modal
        decision = pyautogui.confirm(... ["Disable Pause", "Discard Application", "Submit Application"])
    if wait_span_click(driver, "Submit application", 2, scrollTop=True): date_applied = datetime.now()
    elif errored == "nose": raise Exception("Failed to click Submit application")   # only then escalate
```

**Flow:** each Next page increments the counter → at 15, EITHER the configured human pause resets the counter to 1 (run continues with the same job) OR a screenshot is taken, the ledger records "stuck", and the exception unwinds to the per-job failure island (`failed_job(...); discard_job(); continue`).
**Invariant:** the loop can never spin unbounded — every 15th iteration resolves by human reset or raise; a "stuck" modal must not reach submit (the finally-block skips both the review pause and treats submit-click failure as fatal ONLY for the "nose" case); one bad job still ends in discard+ledger row, never aborts the run.
**Probe:** no upstream test pins this path (orchestration-level caveat, same as job-run-orchestration recorded) — source-grounded seam; adjacent evidence: full suite executes green (56 passed) but does not exercise apply_to_jobs. Direct probe: read :1018–1031 against the invariant above.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "Auto_job_applier_linkedIn", query: "apply_to_jobs answer_questions modal", limit: 6 });
// → runAiBot.answer_questions runAiBot.py :435-714 · runAiBot.apply_to_jobs :841-1113
```

## Verdict
Adopt the bounded counter with human-reset semantics, the three-value errored vocabulary driving finally-policy, and screenshot-before-raise; adapt the threshold (15) and alert copy; omit pyautogui in headless ports (replace with your HITL queue). Complements form-question-answering (which owns answering INSIDE one page) and job-run-orchestration (which owns the outer loop) — this capsule owns the LOOP-BOUNDARY between them.
