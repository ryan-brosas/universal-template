<!-- capsule-v2 -->
# Preferred-resume picker — which uploaded resume should the bot select, and when may it click at all?

**Source:** EasyApplyJobsBot CC BY-NC-SA 4.0 (learn-only: patterns + control flow, zero verbatim reuse) `main@70fe7484ebe78646fc8e2dd2612459f37eed7a9f`; Codebase Memory `EasyApplyJobsBot`. **Question:** given N account resumes and a 1-based user preference, when is clicking justified and what proof is required first?

## Required-upload probe → aria-label-verified pick (dead error branch documented)
**Path/Symbol:** `linkedin.py:Linkedin.chooseResume` (:301–315).
**Signature:** `chooseResume(self) -> None`.
**Data Shape:** resumes = `//div[contains(@class,'ui-attachment--pdf')]` elements; index = `config.preferredCv - 1`; verification label EXACTLY `"Select this resume"`.

### Decisive source
```python
self.driver.find_element(By.CLASS_NAME, "jobs-document-upload__title--is-required")
resumes = self.driver.find_elements(By.XPATH, "//div[contains(@class, 'ui-attachment--pdf')]")
if (len(resumes) == 1 and resumes[0].get_attribute("aria-label") == "Select this resume"):
    resumes[0].click()
elif (len(resumes) > 1 and resumes[config.preferredCv-1].get_attribute("aria-label") == "Select this resume"):
    resumes[config.preferredCv-1].click()
elif (type(len(resumes)) != int):   # ALWAYS False — dead branch
    utils.prRed("❌ No resume has been selected please add at least one resume ...")
```

**Flow:** acts ONLY when the upload-required marker resolves (cheap CLASS_NAME probe) → enumerates pdf attachment cards → clicks the single card OR the preferredCv-th card, but only AFTER verifying its aria-label equals 'Select this resume' → otherwise NOTHING is clicked; whole body try/except pass (silent).
**Invariant:** probe-before-enumerate avoids touching forms that never ask; label verification prevents clicking a wrong widget even if class names drift; silent failure keeps the apply walk alive (submit proceeds unselected and LinkedIn's own downstream error surfaces). DEAD-CODE TRAP: `type(len(resumes)) != int` is always False (`len()` returns int), so the friendly no-resume message is UNREACHABLE — do not resurrect it without fixing the condition (e.g. test `len(resumes) == 0` first).
**Probe:** `grep -n "preferredCv\|Select this resume\|type(len(resumes))\|ui-attachment--pdf\|is-required" linkedin.py` ⇒ :304/:306/:307/:309/:310/:311.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "EasyApplyJobsBot", query: "chooseResume preferredCv", limit: 10 });
await mcp.codebase_memory.get_code_snippet({ project: "EasyApplyJobsBot", qualified_name: "EasyApplyJobsBot.linkedin.Linkedin.chooseResume" });
```

## Verdict
Adopt: required-probe → enumerate → verify-label → click discipline with 1-based user config. Adapt: fail loudly or record an outcome instead of the dead elif + bare except. Omit: nothing structural. Contrast `form-question-answering`'s random-index≥1 last resort — here NO click beats a wrong click. Coverage caveat: no tests; six-point grep pin + graph parity.
