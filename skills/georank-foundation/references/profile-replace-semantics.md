<!-- capsule-v2 -->
# Profile extraction replace-semantics — why does a re-run CLEAR fields the new crawl didn't find?

**Source:** GEOrank (aeo-georank) Apache-2.0 `main@424a0cf92b37ad63c94ae9dc6f39745189ab7c94`; Codebase Memory `ext-aeo-georank`. **Question:** When an AI-extracted company profile is refreshed, which fields persist and which must be reset — and how do you keep LLM failure from erasing good data?

## Merge-vs-replace dual mode + provider-failure shield
**Path/Symbol:** `backend/app/services/company_profile.py`: `extract_company_profile` :260–288, `build_company_profile_values` :317–384 (`replace: bool`), `calculate_company_geo_profile` :291–315, `normalize_company_name` :171, `_KNOWN_TECH_TERMS` tech sniffing; pipeline consumer `_run_clean` in `tasks/process.py` :366–461.
**Signature:** `build_company_profile_values(company: Company, profile: dict, *, replace: bool = False) -> dict`.
**Data Shape:** Profile keys: name/description/short_description/category/headquarters/funding_stage/employee_count/founded_date(YYYY-MM or YYYY-MM-DD)/tags≤6/tech_stack≤8/team_members≤6 + private `_provider_succeeded` flag.

### Decisive source
```python
"""Pipeline refreshes use ``replace=True`` so fields absent from the current
crawl cannot be silently satisfied by stale values from an older run.
Opportunistic hydration keeps the existing merge behavior."""
if profile.get("description"):
    values["description"] = profile["description"]
elif replace:
    values["description"] = None          # explicit NULL — do NOT keep last run's value
...
if founded_date len == 7: founded_date += "-01"   # YYYY-MM → day-1 normalization
```
Failure shield in extract:
```python
try:
    extracted = await ai_client.extract_company_info(html)
    provider_succeeded = True
except Exception:
    extracted = {}                        # heuristic fallback result stands; LLM adds nothing
for key in (...):
    if extracted.get(key) not in (None, "", []):
        profile[key] = extracted[key]     # non-empty AI fields override heuristics only
```

**Flow:** deterministic HTML fallback parse (title/meta/keywords→tags/known-tech-term scan) → AI extraction overrides non-empty keys only → geo score computed from homepage via the diagnose scorers → `build_company_profile_values(replace=True)` in the PIPELINE (stale data dies with its source page) vs merge in opportunistic hydration → post-write completeness check raises if required fields are still missing.
**Invariant:** The `_provider_succeeded` marker decides metering (tokens counted only on success) but NEVER gates persistence — a heuristic-only profile is still written. Replace-mode emits explicit None so a refresh can't leave zombie values from a previous crawl. Name normalization guards against the AI returning legal suffixes/marketing noise as the identity.
**Probe:** `backend/tests/test_company_profile.py::test_build_values_replace_*` (merge vs replace matrices incl. date coercion).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-aeo-georank", query: "build_company_profile_values", limit: 5 });
// verified line-exact: company_profile.py :317–384
```

## Verdict
Adopt dual-mode field mapping for any AI-refreshable structured record; adapt field caps/date formats; keep the provider-succeeded/metering split. Direct tests green under real runner.
