<!-- capsule-v2 -->
# Form-question answering — how do I map arbitrary Easy Apply questions (select/radio/text/textarea/checkbox) to safe answers?

**Source:** Auto_job_applier_linkedIn MIT `main@0ca5550f8aa80027621cfc17a30fceba05705f84` (`runAiBot.answer_questions` :435–714); contrast LinkedIn-Easy-Apply-Bot Apache-2.0 `ans_question` (:601–653). Codebase Memory `Auto_job_applier_linkedIn`. **Question:** what widget dispatch order and answer-fallback ladder lets a bot fill unknown application forms without wrong-submissions?

## answer_questions widget dispatch
**Path/Symbol:** `runAiBot.py:answer_questions(modal, questions_list, work_location, job_description=None)` (:435–714); helpers `answer_common_questions` (:429–431), `extract_years_of_experience` (:353–359); AI fallback `modules/ai/connections.answer_question` (stub-tested).
**Signature:** iterates `.//div[@data-test-form-element]`; per question probes in order: `.//select` → `fieldset[@data-test-form-builder-radio-button-form-component="true"]` → `input[@type='text']` → `textarea` → `input[@type='checkbox']`.
**Data Shape:** every answered question is recorded as a tuple `(label, answer, kind, prev_answer)` into a set — an audit log of what the bot changed; `overwrite_previous_answers` gates re-filling pre-filled fields.

### Decisive source
```python
try:
    select.select_by_visible_text(answer)
except NoSuchElementException:
    # exact text isn't an option → snap to nearest real option
    candidate_phrases = ["Decline","not wish","don't wish","Prefer not","not want"] if answer=='Decline' \
        else (["Yes","Agree","I do","I have"] if 'yes' in lower else ["No","Disagree","I don't","I do not"])
    for phrase in candidate_phrases:
        for option in optionsText:
            if phrase.lower() in option.lower() or option.lower() in phrase.lower():
                select.select_by_visible_text(option); matched = True; break
    if not matched:
        select.select_by_index(randint(1, len(select.options) - 1))   # NEVER index 0 ("Select an option")
        randomly_answered_questions.add(...)                          # surfaced to the user post-run
```

**Flow:** classify by probing one widget type at a time → resolve label (visually-hidden span under the label) → keyword-route label to profile field (experience/phone/city/signature/salary-with-current-vs-desired-and-lakhs-vs-monthly variants…) → only when no rule matches AND AI enabled: ask the LLM with the job description as context → on any failure record into `randomly_answered_questions` instead of crashing.
**Invariant:** never submit a blank dropdown (random pick starts at index 1); decline-style answers expand to a phrase family because employers word them differently; the questions_list set makes every mutation auditable after the run. Experience extraction caps at 12 years (`int(match) <= 12`) to ignore "10+ years" boilerplate mismatches.
**Probe:** `tests/test_ai_connections.py::test_answer_question_text_returns_cleaned_answer`, `::test_answer_question_select_snaps_to_allowed_option`, `::test_answer_question_select_passthrough_when_no_option_matches`, `::test_answer_question_none_client_is_safe` — stub-model unit tests pinning exactly this fallback ladder (no network).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "Auto_job_applier_linkedIn", query: "answer_questions", limit: 5 });
// direct test nodes: tests.test_helpers.test_truncate_for_csv_* also indexed
```

## Verdict
Adopt the widget-probe dispatch order, the decline/yes/no phrase-family snapping with random-index-≥1 last resort, and the audit-tuple recording; adapt the label-keyword table and personal-field config to host; omit pyautogui pause dialogs and the specific GitHub-referral answer. Probe caveat: the AI-answer ladder is stub-tested; raw Selenium interactions are source-grounded only.
