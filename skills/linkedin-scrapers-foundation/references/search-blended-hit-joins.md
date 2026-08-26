<!-- capsule-v2 -->
# Blended vs job-search hit joins — how do I rehydrate full entities onto search hits that only carry URNs?

**Source:** linkedin-private-api MIT `master@e083f37`; Codebase Memory `linkedin-private-api`. **Question:** a search hit references its payload by URN — how do the people/companies/joins differ, and what is the porting trap in the jobs path?

## The three fetchers
**Path/Symbol:** `src/repositories/search.repository.ts` — `fetchPeople` (:129–156), `fetchCompanies` (:158–190), `fetchJobs` (:192–235); request twins `src/requests/search.request.ts:searchBlended/searchJobs`.
**Signature:** all three take `{skip, limit, filters?, keywords?}` and return hydrated hit arrays; people/companies go through ONE blended endpoint (`search/blended`, `q=all`, `origin=TYPEAHEAD_ESCAPE_HATCH`) with `resultType` injected into filters; jobs use a dedicated endpoint (`search/hits`, `q=jserpFilters`, `origin=JOB_SEARCH_RESULTS_PAGE`, deco `WebJobSearchHitLite-14`).
**Data Shape:** blended envelope = clusters (`data.elements[].type === 'SEARCH_HITS'`, each cluster holds `.elements[]` of `SearchHitV2` with `targetUrn`) + flat `included[]`; jobs envelope = flat hits (`data.elements[]` of `SearchHit` whose `hitInfo.jobPosting` IS the posting URN) + `included[]` holding TWO entity kinds.

### Decisive source
```ts
// jobs: the URN chain is TWO hops deep — resolve it iteratively
const keyedPostings = keyBy(jobPostings, 'entityUrn');   // $type === JobPosting
const keyedCompanies = keyBy(companies, 'entityUrn');    // $type === organization.Company
response?.data?.elements.map(searchHit => {
  const jobPosting = keyedPostings[searchHit.hitInfo.jobPosting];      // hop 1: hit -> posting
  const company = keyedCompanies[jobPosting.companyDetails.company];   // hop 2: posting -> company
  return { ...searchHit, hitInfo: { ...searchHit.hitInfo,
    jobPosting: { ...jobPosting, companyDetails: { ...jobPosting.companyDetails, company } } } };
});
// people/companies: ONE hop off targetUrn
return searchHits.map(hit => ({ ...hit, profile: profilesByUrn[hit.targetUrn] }));
```

**Flow:** blended path flattens nested clusters first, then single-hop joins `targetUrn → included[$type=MiniProfile|MiniCompany]`; companies additionally derive `companyId = entityUrn.replace('urn:li:fs_miniCompany:', '')`; jobs path walks hit→posting→company and rebuilds the hit object inside-out so the final type nests populated entities at every level.
**Invariant:** join keys are RAW URN strings end-to-end — never strip the `urn:` prefix on the lookup side (only derived convenience ids like `companyId`/`profileId` get prefix-stripped); missing keys degrade to `undefined` fields (spread of undefined-safe), never throws. The jobs path breaks if you reuse the single-hop pattern: `hitInfo.jobPosting` is a URN there but an OBJECT after population.
**Probe:** `test/search/search-repository.spec.ts:577–620` — "should populate job posting" asserts `jobs[0].hitInfo.jobPosting.$type === 'com.linkedin.voyager.jobs.JobPosting'` and "should populate job company" asserts `...companyDetails.company.$type === 'com.linkedin.voyager.organization.Company'` over factory envelopes wired exactly as hit→postingUrn→companyUrn (`test/search/search-factories.ts:createSearchJobsResponse`). People twin pinned at :78/:99 (`people[0].profile` equals included row minus pictureUrls).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "linkedin-private-api", query: "SearchRepository fetchJobs fetchPeople fetchCompanies", limit: 10 });
```

## Verdict
Adopt the URN-keyed hydration ladder: flatten clusters → `$type` filter included[] → keyBy entityUrn → iterative URN-chain resolution for multi-hop payloads. Adapt endpoint names/decoration ids (they rotate) and which convenience ids you derive. Omit nothing — this is the search-plane counterpart of included-envelope-hydration (single-envelope hydration) and scroller-factory-repositories (who calls these fetchers).
