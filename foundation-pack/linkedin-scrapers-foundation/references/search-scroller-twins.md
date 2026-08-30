<!-- capsule-v2 -->
# Search-scroller twins — when is a subclass NOT worth a class? (thin parameterization over a shared state machine)

**Source:** linkedin-private-api MIT `master@e083f37`; Codebase Memory `linkedin-private-api`. **Question:** how do PeopleSearchScroller/JobSearchScroller/CompanySearchScroller relate to SkipLimitScroller, and where is the reuse boundary?

## The three twins
**Path/Symbol:** `src/scrollers/people-search.scroller.ts:PeopleSearchScroller` (47L), `job-search.scroller.ts:JobSearchScroller` (47L), `company-search.scroller.ts:CompanySearchScroller` (39L); base `skip-limit-scroller.ts`.
**Signature:** each twin adds ONLY private config fields + an injected fetch closure typed to its hit shape, then `async fetch() { return this.fetchX({ skip: this.skip, limit: this.limit, ...config }); }` — zero paging logic of their own.
**Data Shape:** `FetchPeople/FetchJobs/FetchCompanies` type aliases name the closure contract `({skip?, limit?, filters?, keywords?}) => Promise<Hit[]>`; the scroller holds config but NO data until scrollNext.

### Decisive source
```ts
export class JobSearchScroller extends SkipLimitScroller<JobSearchHit> {
  private fetchJobs: FetchJobs;          // injected bound closure
  private filters?: JobSearchFilters;
  private keywords?: string;
  constructor({ fetchJobs, skip = 0, limit = 10, filters, keywords }) {
    super({ skip, limit });              // base owns the offset/limit latch machine
    this.fetchJobs = fetchJobs; this.filters = filters; this.keywords = keywords;
  }
  async fetch(): Promise<JobSearchHit[]> {   // ONE override point
    return this.fetchJobs({ skip: this.skip, limit: this.limit, filters: this.filters, keywords: this.keywords });
  }
}
```

**Flow:** repository factory builds the twin with a `.bind(this)`-ed fetcher → base-class scrollNext advances skip and calls the twin's fetch → twin forwards CURRENT config + cursor to the closure → hydration happens in the repository's private fetcher, not the scroller.
**Invariant:** ALL end-of-results / rewind / counter semantics live in SkipLimitScroller (skip-limit-scroller capsule); a twin that re-implements any paging breaks the single-machine invariant. The class earns its existence only by TYPING the closure + carrying per-entity config — if your variant has neither, pass a lambda instead of subclassing.
**Probe:** `test/search/search-repository.spec.ts` drives all three through the same mocked-axios matrix (:27–207 people incl. previous-page scroll :180, :324–519 companies, :525–620 jobs) — identical assertions prove the base machine serves all entities; factory wiring pinned by `client.search.searchJobs()` returning a scroller whose first scrollNext hits the expected URL.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "linkedin-private-api", query: "PeopleSearchScroller JobSearchScroller SkipLimitScroller", limit: 10 });
```

## Verdict
Adopt the test: subclass a paging base ONLY to bind a typed fetch closure + entity config; keep every cursor semantic in the base. Adapt hit types/filters per endpoint. Omit new classes for filter-only variants — searchOwnConnections shows those are one-line filter rewrites at the repository layer (scroller-factory-repositories).
