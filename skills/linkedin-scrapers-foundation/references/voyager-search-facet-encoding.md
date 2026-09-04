<!-- capsule-v2 -->
# Voyager search-facet encoding — how do I encode LinkedIn search filters into the Voyager API's `filters`/`selectedFilters` query grammar (not the URL builder)?

**Source:** open-linkedin-api MIT `main@5feee360ec26719d07d5e67638045e751b48a74c` (`linkedin.py`); Codebase Memory `open-linkedin-api`. **Question:** what is the API-side facet grammar — the `List((key,value:List(...)))` filter strings for people and the `selectedFilters` dict + query-string assembly for jobs — and how does it differ from the URL-param builder?

## search_people filter list + search_jobs selectedFilters + query-string assembly
**Path/Symbol:** `linkedin.py:Linkedin.search_people` (:305–455), `search_companies` (:457–491), `search_jobs` (:493–656), and the shared `search` pagination loop (:203–303, see voyager-pagination.md).
**Signature:** `search_people(keywords=None, connection_of=None, network_depths=None, current_company=None, past_companies=None, regions=None, industries=None, schools=None, contact_interests=None, service_categories=None, ...) -> List[Dict]`; `search_jobs(keywords=None, companies=None, experience=None, job_type=None, job_title=None, industries=None, location_name=None, remote=None, listed_at=86400, distance=None, limit=-1, offset=0) -> List[Dict]`.
**Data Shape:** two distinct encodings — people/companies build a `filters` list of `(key:resultType,value:List(PEOPLE))`-style strings joined by commas inside `List({})`; jobs build a `selectedFilters` dict whose values are `List(<comma-joined>)` strings, then serialize the whole query dict into a parenthesized GraphQL `query` string via placeholder substitution + `{`→`(` / `}`→`)` replacement.

### Decisive source
```python
# PEOPLE: a list of (key,value:List(...)) filter strings, joined inside List({})
filters = ["(key:resultType,value:List(PEOPLE))"]
if regions:
    stringify = " | ".join(regions)                    # multi-value separator is " | "
    filters.append(f"(key:geoUrn,value:List({stringify}))")
if network_depths:
    filters.append(f"(key:network,value:List({' | '.join(network_depths)}))")
params = {"filters": "List({})".format(",".join(filters))}   # "List((key:...,value:...),(key:...))"

# JOBS: a selectedFilters dict with List(...) values, then a query-string build
query = {"origin": "JOB_SEARCH_PAGE_QUERY_EXPANSION"}
query["selectedFilters"] = {}
if companies:  query["selectedFilters"]["company"] = f"List({','.join(companies)})"
if remote:     query["selectedFilters"]["workplaceType"] = f"List({','.join(remote)})"
query["selectedFilters"]["timePostedRange"] = f"List(r{listed_at})"   # r-prefixed seconds
query["spellCorrectionEnabled"] = "true"
query_string = (str(query).replace(" ", "").replace("'", "")
    .replace("KEYWORD_PLACEHOLDER", keywords or "")
    .replace("LOCATION_PLACEHOLDER", location_name or "")
    .replace("{", "(").replace("}", ")"))
# → "(origin:JOB_SEARCH_PAGE_QUERY_EXPANSION,selectedFilters:(company:List(163253),timePostedRange:List(r86400)),spellCorrectionEnabled:true)"
```

**Flow:** people/companies → build the `filters` string list (resultType anchors it; each optional facet appends `(key:<k>,value:List(<vals>))` with `" | "`-joined values) → wrap as `List(...)` and pass as the `filters` param → `search()` paginates (voyager-pagination). Jobs → build `query` dict with `origin`, a `selectedFilters` sub-dict (company/experience/jobType/title/industry/distance/workplaceType/timePostedRange), and `spellCorrectionEnabled` → serialize via placeholder-substitution + brace→paren rewrite → send as the `query` param to `/voyagerJobsDashJobCards?q=jobSearch&decorationId=...&count=...&start=...`.
**Invariant:** the multi-value separator is `" | "` (pipe-space-pipe) inside `value:List(...)` for people, but plain `,` (comma) inside `List(...)` for jobs — a porter mixing the two gets a malformed filter. The `timePostedRange` value is `r` + seconds-since-posted (`r86400` = 24 h). The jobs `query` must be a *string* (not a dict) because it's URL-encoded into the `query` param; the brace→paren rewrite is what turns Python dict syntax into Voyager's parenthesized grammar. `origin` differs by surface (`GLOBAL_SEARCH_HEADER` for people search, `JOB_SEARCH_PAGE_QUERY_EXPANSION` for jobs) and is required.
**Probe:** no upstream tests for the search encoders — coverage caveat recorded; behavior pinned by reading linkedin.py:305–656 at HEAD. Graph anchors resolve `search_people`, `search_jobs`, `search_companies`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "open-linkedin-api", query: "search_people", limit: 10 });
await mcp.codebase_memory.search_graph({ project: "open-linkedin-api", query: "search_jobs", limit: 10 });
```

## Verdict
Adopt the two-grammar split (people `filters` `(key,value:List(...))` strings vs jobs `selectedFilters` dict + brace→paren query-string assembly), the `" | "` vs `,` multi-value separator distinction, and the `r<seconds>` time-posted encoding; adapt facet key names (geoUrn/industry/currentCompany/network/workplaceType) as LinkedIn rotates them and your search surface; omit the hard-coded `decorationId`/`queryId` (rotate) and the `keyword_title`/`title` backward-compat alias. Caveat: source-grounded only, no test coverage.
