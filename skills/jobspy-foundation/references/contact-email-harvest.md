<!-- capsule-v2 -->
# Contact-email harvest — how do recruiter emails travel from free-text descriptions into JobPost.emails and the output column?

**Source:** JobSpy MIT `main@fda080a373e8`; Codebase Memory `JobSpy`. **Question:** Where exactly is extract_emails_from_text wired per site, and how do missing vs empty descriptions differ downstream?

## One regex helper, six wirings
**Path/Symbol:** helper `jobspy/util.py:extract_emails_from_text` (:170–174); wiring matrix — `linkedin/__init__.py:244`, `google/__init__.py:199` (unguarded); `glassdoor/__init__.py:215`, `indeed/__init__.py:236`, `ziprecruiter/__init__.py:174` (guarded by 'if description'); `naukri/__init__.py:201` ('description or ""'); `bdjobs/__init__.py:32` imports but NEVER calls it (dead import); flatten join guard `jobspy/__init__.py:142–143`.
**Signature:** `extract_emails_from_text(text: str) -> list[str] | None`.
**Data Shape:** None ONLY for falsy text; [] when text exists but contains no addresses (executed P9); regex byte-for-byte: r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}".

### Decisive source
```python
def extract_emails_from_text(text):
    if not text: return None
    email_regex = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
    return email_regex.findall(text)

# flatten join guard turns [] into None, never empty string:
job_data["emails"] = (", ".join(job_data["emails"]) if job_data["emails"] else None)
```

**Flow:** description text (markdown/plain per DescriptionFormat) -> findall -> JobPost.emails list -> per-job dict -> comma-join into the emails column (guarded so [] collapses to None).
**Invariant:** the None-vs-[] distinction survives only until the flatten join, which erases it to None; LinkedIn and Google call the helper even when description is None (safe: falsy -> None); Naukri's 'or ""' makes the guard redundant; BDJobs forgetting to wire the helper means its jobs NEVER carry emails. The regex accepts subdomain-rich hosts and '+tag' locals, rejects 'bad@@no' (executed).
**Probe:** executed P9: 'mail a@b.co / x.y%z+1@mail.example.com / bad@@no' -> ['a@b.co', 'x.y%z+1@mail.example.com']. Wiring matrix pinned by line-level greps recorded in state.md. trace_path inbound callers_total=11 across six adapters.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.trace_path({ project: "JobSpy", function_name: "extract_emails_from_text", direction: "inbound", depth: 2 });
```

## Verdict
Adopt harvesting contact emails from descriptions with a strict single-pass regex and a None-for-missing/list-for-found shape. Adapt the wiring guard to whether your description field can be None. Omit per-site divergence like BDJobs' dead import — wire it once at the JobPost boundary instead. Coverage caveat: no tests; regex behavior pinned by executed excerpt.
