
`<!-- capsule-v2 -->`
# Job detail URN plane — how do I fetch a job posting and its skills when IDs are URNs and errors hide inside HTTP 200?

**Source:** open-linkedin-api MIT `main@5feee360ec26719d07d5e67638045e751b48a74c`; Codebase Memory `open-linkedin-api`. **Question:** what wire shapes do the job detail endpoints use, and where can failure masquerade as success?

## Job detail plane
**Path/Symbol:** `linkedin.py:Linkedin.get_job` (:1674–1694), `Linkedin.get_job_skills` (:1765–1787).
**Signature:** `get_job(job_id: str) -> Dict`; `get_job_skills(job_id: str) -> Dict`.
**Data Shape:** `GET /jobs/jobPostings/{job_id}?decorationId=com.linkedin.voyager.deco.jobs.web.shared.WebLightJobPosting-23` returns the posting envelope; skills live on a DIFFERENT dash service keyed by a FULL URN used as a percent-encoded PATH segment: `/voyagerAssessmentsDashJobSkillMatchInsight/urn%3Ali%3Afsd_jobSkillMatchInsight%3A{job_id}` with deco `FullJobSkillMatchInsight-17`.

### Decisive source
```python
data = res.json()
if data and "status" in data and data["status"] != 200:
    self.logger.info("request failed: {}".format(data["message"]))
    return {}
return data

# skills: the URN *is* the path segment (pre-encoded)
res = self._fetch(
    f"/voyagerAssessmentsDashJobSkillMatchInsight/urn%3Ali%3Afsd_jobSkillMatchInsight%3A{job_id}",
    params={"decorationId": "com.linkedin.voyager.dash.deco.assessments.FullJobSkillMatchInsight-17"},
)
```

**Flow:** bare numeric job id → posting fetch with versioned deco → SAME id re-wrapped into a full fsd_jobSkillMatchInsight URN, URL-encoded, spliced INTO the path of the assessments service.
**Invariant:** HTTP 200 does NOT imply success — some Voyager endpoints embed an application error (`{"status": <code>, "message": ...}`) INSIDE the 200 envelope; every consumer re-checks `data["status"]` and degrades to `{}`. The two endpoints share the bare id but different URN namespaces; the skills URN must be pre-percent-encoded (%3A colons) because it rides as a path SEGMENT, not a query value. Deco suffixes rotate — pin to fixtures.
**Probe:** no upstream tests (runner block recorded). Byte-exact grep resolves :1778 (URN path) / :1690+:1783 (embedded-status guards):
```bash
grep -n 'fsd_jobSkillMatchInsight|"status" in data' open_linkedin_api/linkedin.py
```

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "open-linkedin-api", query: "get_job", limit: 5 });
await mcp.codebase_memory.search_graph({ project: "open-linkedin-api", query: "get_job_skills", limit: 5 });
```

## Verdict
Adopt the embedded-status guard as a mandatory SECOND error check after every Voyager read, and URN-as-path-segment addressing for dash sub-services; adapt deco ids (rotate) and endpoint names; omit hard-coded message interpolation. Contrast: `decoration-id-response-shaping` covers deco VERSIONING from the private-api twin; this capsule adds the embedded-error envelope + segment encoding from THIS repo. Caveat: source-grounded only.
