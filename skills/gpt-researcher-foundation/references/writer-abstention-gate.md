<!-- capsule-v2 -->
# Writer abstention gate — what does the report generator return when research gathered nothing?

**Source:** gpt-researcher Apache-2.0 `main@5d84d2f5553e70a2765a8ff3a0d2672d60437ce8`; Codebase Memory `gpt-researcher`. **Question:** How does the system avoid emitting a confident, sourced-looking report from an empty context?

## Empty-context refusal in ReportGenerator.write_report
**Path/Symbol:** `gpt_researcher/skills/writer.py:77-88`.
**Signature:** inside `async def write_report(self, existing_headers=[], relevant_written_contents=[], ext_context=None, custom_prompt="", available_images=None) -> str`
**Data Shape:** Accepts context as list OR string; refusal is a plain sentence string returned INSTEAD of a report (callers treat it as the report text).

### Decisive source
```python
# Guard against fabricating a report from nothing: if no research content was
# gathered (every retriever returned empty / was blocked / rate-limited), don't
# silently write a confident, sourced-looking report - abstain so it is visible.
_ctx = "\n".join(context) if isinstance(context, list) else str(context or "")
if not _ctx.strip():
    return (
        f'I could not gather any source material for "{self.researcher.query}". '
        "No sources were retrieved (searches may have returned nothing or been "
        "blocked), so I am not able to produce a reliable, sourced report."
    )
```

**Flow:** write_report normalizes whatever context shape arrived → whitespace-only counts as empty → refusal short-circuits BEFORE prompt construction, image embedding instructions, or any LLM spend → otherwise proceeds to `generate_report` with subtopic/custom/generic prompt selection and system+user message split (with a single retry collapsing both roles into one user turn on failure).
**Invariant:** abstention must fire before cost accrues — moving the check after `generate_report` would still bill the call. The refusal names possible CAUSES (empty/blocked/rate-limited) so operators can diagnose; keep that phrasing when porting.
**Probe:** battery P15a GREEN (`I could not gather any source material` ×1). Coverage caveat: no dedicated upstream test for this branch.
