<!-- capsule-v2 -->
# Job-run orchestration — how do I drive the full search→filter→apply→log loop with caps, dry-run, and crash-safe logging?

**Source:** Auto_job_applier_linkedIn MIT `main@0ca5550` (`runAiBot.apply_to_jobs` :841–1113, `run` :1116–1131); cross-checked EasyApplyJobsBot CC-BY-NC `linkJobApply` (:127–299) and LinkedIn-Easy-Apply-Bot Apache-2.0 `applications_loop` (:242–313). Codebase Memory `Auto_job_applier_linkedIn`. **Question:** what control-flow structure (caps, counters, pagination exit, per-job isolation) keeps a long unattended run safe?

## apply_to_jobs outer loop
**Path/Symbol:** `runAiBot.py:apply_to_jobs(search_terms)` (:841–1113) with per-job pipeline inside; caps: `switch_number` page budget, `dailyEasyApplyLimitReached` flag (:726), `maxApplicationsPerRun`-style counters; EasyApplyJobsBot variant: `reachedCap` triple-break (:283–288).
**Signature:** per job: `get_job_main_details → check_blacklist → get_job_description → [AI extract_skills] → Easy-Apply detection ladder → answer_questions → submit → submitted_jobs/failed_job`; global counters `easy_applied_count / external_jobs_count / failed_count / skip_count`.
**Data Shape:** two append-only ledgers — applied CSV (18 columns via DictWriter + truncate_for_csv cells) and failed CSV (9 columns incl. stack trace + screenshot name); both header-on-first-write.

### Decisive source
```python
# Easy-Apply detection is a three-check escalation (button label → in-app URL flag → modal probe):
is_easy_apply = try_xp(driver, ".//button[contains(@class,'jobs-apply-button') ... contains(@aria-label,'Easy')]")
if not is_easy_apply:
    in_app_apply = driver.find_element(By.XPATH, ".//a[contains(@href,'openSDUIApplyFlow=true')]") ...
if not is_easy_apply:
    tabs_open = len(driver.window_handles); apply_button.click()
    if len(driver.window_handles) > tabs_open:      # new tab ⇒ EXTERNAL application, not Easy Apply
        driver.close(); driver.switch_to.window(linkedIn_tab)
    else: find_by_class(driver, "jobs-easy-apply-modal") → is_easy_apply = True
...
except Exception as e:                               # one bad job never kills the run
    critical_error_log("Somewhere in Easy Apply process", e)
    failed_job(...); discard_job(); continue
```

**Flow:** for each search term → navigate → UI filters → while pages < cap: collect cards → per job run the guarded pipeline → write success or failure ledger row immediately → paginate via `Page {n+1}` aria-label button (missing ⇒ end). External-apply path records the outbound link then returns to the LinkedIn tab.
**Invariant:** every job is wrapped so failure = ledger entry + modal discard + continue (never abort); caps checked at THREE nested levels with matched breaks (job loop/page loop/url loop); daily-limit detection flips a latch that unwinds cleanly at the top of `run()`; window-closed exceptions re-raise past the per-job handler because they mean the SESSION died.
**Probe:** no upstream tests pin the orchestrator — coverage caveat recorded. Adjacent tested seams feeding it: AI-answer stub tests (`test_answer_question_*`) and CSV truncation tests (`test_truncate_for_csv_*`). Graph anchor: `runAiBot.answer_questions`, `get_applied_job_ids`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "Auto_job_applier_linkedIn", query: "answer_questions", limit: 5 });
```

## Verdict
Adopt the per-job exception island, immediate dual-ledger writes, three-level caps with matched breaks, and tab-count external detection; adapt filter lists, budgets, and ledger schemas to host; omit pyautogui confirm() pauses and donate()/sponsor nags. Caveat: orchestration itself source-grounded only; its leaf contracts are test-pinned.
