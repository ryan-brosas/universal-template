
`<!-- capsule-v2 -->`
# Universal-name entity lookup — how do I resolve companies AND schools through ONE endpoint keyed by public slug?

**Source:** open-linkedin-api MIT `main@5feee360ec26719d07d5e67638045e751b48a74c`; Codebase Memory `open-linkedin-api`. **Question:** what does a slug-keyed entity fetch look like when two entity kinds share one namespace?

## Slug-keyed entity fetch
**Path/Symbol:** `linkedin.py:Linkedin.get_school` (:1132–1157), `Linkedin.get_company` (:1159–1184).
**Signature:** `get_school(public_id) -> Dict`; `get_company(public_id) -> Dict`.
**Data Shape:** BOTH call `GET /organization/companies?q=universalName&universalName=<public_slug>` with the SAME deco `com.linkedin.voyager.deco.organization.web.WebFullCompanyMain-12`; response is an elements[] envelope whose FIRST row is the resolved entity.

### Decisive source
```python
params = {
    "decorationId": "com.linkedin.voyager.deco.organization.web.WebFullCompanyMain-12",
    "q": "universalName",
    "universalName": public_id,
}
res = self._fetch(f"/organization/companies", params=params)      # get_company
# get_school builds the identical request via f"...?{urlencode(params)}"
...
company = data["elements"][0]                                     # first-row take
```

**Flow:** public slug (the vanity name from /company/<slug> URLs) → universalName query → single-row envelope → elements[0].
**Invariant:** schools ARE companies server-side — one endpoint, one decoration, one parser serves both kinds; callers differ only by intent. The lookup key is the SLUG, never a numeric id. The first-row take is guarded ONLY by the embedded-status check (see job-detail-urn-plane) — an empty-but-200 elements array would raise IndexError, so ports must add an emptiness guard the original lacks. Two param styles coexist (params dict vs inline urlencode) with identical wire results — style is not semantics.
**Probe:** no upstream tests (runner block recorded). Byte-exact grep resolves :1142-1144 (school params) / :1169-1171 (company params):
```bash
grep -n 'universalName|WebFullCompanyMain' open_linkedin_api/linkedin.py
```

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "open-linkedin-api", query: "get_company", limit: 5 });
await mcp.codebase_memory.search_graph({ project: "open-linkedin-api", query: "get_school", limit: 5 });
```

## Verdict
Adopt slug-keyed universal-name resolution with a shared projection for sibling entity kinds; adapt the deco suffix (rotates) and ADD the missing emptiness guard when porting; omit the duplicated method bodies (collapse to one parameterized fetch). Caveat: source-grounded only.
