<!-- capsule-v2 -->
# Browser-title ledger identity — how do I derive auditable ledger identity (title/company) for an application row when the only surviving carrier is the browser tab title?

**Source:** LinkedIn-Easy-Apply-Bot Apache-2.0 `master@8471c58b39e2a3bb3f4a2deb1e3c410e7fda7e0e` (`write_to_file` :372–387; caller `apply_to_job` :368); Codebase Memory `LinkedIn-Easy-Apply-Bot`. **Question:** what does positional splitting of `document.title` into ledger fields guarantee, and where exactly does it degrade?

## Positional `' | '` split whose index IS the field, regex-normalized per part

**Path/Symbol:** `easyapplybot.py:EasyApplyBot.write_to_file` (:372–387), inner helper `re_extract`; caller passes `self.browser.title` (:368).
**Signature:** `write_to_file(button, jobID, browserTitle, result) -> None`; inner `re_extract(text, pattern) -> str | None`.
**Data Shape:** LinkedIn job tab titles arrive as `'Job Title | Company | LinkedIn'` — `split(' | ')` makes part-index the field identity (0=job, 1=company); the appended row is `[timestamp, jobID, job, company, attempted, result]` (attempted half owned by easy-apply-button-sentinel; outcome vocabulary by string-outcome-channel).

### Decisive source
```python
def write_to_file(self, button, jobID, browserTitle, result) -> None:
    def re_extract(text, pattern):
        target = re.search(pattern, text)
        if target:
            target = target.group(1)
        return target                      # None when NOTHING matches

    timestamp: str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    attempted: bool = False if button == False else True
    job = re_extract(browserTitle.split(' | ')[0], r"\(?\d?\)?\s?(\w.*)")
    company = re_extract(browserTitle.split(' | ')[1], r"(\w.*)")   # [1]: IndexError if no ' | '
    toWrite: list = [timestamp, jobID, job, company, attempted, result]
    with open(self.filename, 'a+') as f:
        writer = csv.writer(f)
        writer.writerow(toWrite)
```

**Flow:** deep-link navigation (`get_job_page`) decides nothing about title shape → outcome branches complete → `apply_to_job` hands the CURRENT tab title to `write_to_file` → positional split assigns fields by index → each part is regex-normalized independently (title pattern also strips a leading paren/digit prefix like `(2) `) → append-mode CSV row. Degradation is asymmetric BY MECHANISM: the regex degrades per-PART (non-matching text becomes a `None` cell), while the bare `[1]` index degrades per-ROW — a separator-less title (login/authwall/error tab such as "Sign In to LinkedIn") raises `IndexError`. Crash scope is bounded by applications_loop's whole-cycle island `except Exception as e: print(e)` (:313–314): the run survives but that job's ledger row is silently lost — printed to stdout, never logged.
**Invariant:** positional title-splitting buys zero-DOM-dependence identity (it survives card-DOM loss at modal/deep-link time) at the price of an unguarded separator assumption: every field after index 0 is one missing `' | '` away from losing the whole row. If you port it, guard `len(parts) > 1` before indexing (or prefer card-DOM extraction) and keep per-part normalization total so one malformed field can never erase the audit row's other columns.
**Probe:** repo ships no test suite — coverage caveat recorded. Executed byte-for-byte with the EXACT source patterns at HEAD 8471c58: `'(2) Data Engineer'` ⇒ `'Data Engineer'` (paren-digit strip works); `'Senior Software Engineer'` / `'AIMQ DEVELOPMENT LLC'` extracted cleanly from `'… | … | LinkedIn'`; `'Sign In to LinkedIn'.split(' | ')[1]` ⇒ **IndexError** (row-loss trap confirmed); digit-only part `'7'` backtracks through the optionals to `'7'` — so `re_extract` yields `None` only when nothing matches (empty/symbol-only parts). `grep -n "except Exception as e:\|print(e)" easyapplybot.py` ⇒ :313/:314 island bounds the crash. check_index_coverage(easyapplybot.py, requirements.txt) ⇒ no_recorded_issue + metadata_match @ gen 2026-08-23T00:13:15Z.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.trace_path({ project: "LinkedIn-Easy-Apply-Bot", function_name: "write_to_file", direction: "inbound", depth: 2 });
// ⇒ apply_to_job hop 1, apply_loop hop 2 (executed this pass)
await mcp.codebase_memory.get_code_snippet({ project: "LinkedIn-Easy-Apply-Bot", qualified_name: "LinkedIn-Easy-Apply-Bot.easyapplybot.EasyApplyBot.write_to_file" });
// ⇒ :372-387 verbatim body (executed)
```

## Verdict
Adapt: keep the timestamped append-only row and per-part regex normalization, ADD the separator-count guard before any indexed part, and re-verify the live title format before production (the `'Job | Company | LinkedIn'` shape is a 2024-era observation, not a contract). Omit deriving identity from tab state you don't control when a card/container source still exists — suite twins that degrade more gracefully: job-topcard-middot-triplet (DOM-container `'·'` split where part-index IS identity WITH guarded vocabulary fallbacks), pipe-row-three-island-extraction (per-field try-islands degrading to `""`, and the middot→pipe folding that collides content WITH this very delimiter), wheel-bracketed-topcard-reader (per-field independent degradation), relative-posted-time-normalization (declarative noisy-string parsing). Contrast within this repo: easy-apply-button-sentinel owns the OBJECT half of the same row (attempted from the sentinel); this seam owns only the IDENTITY half.
