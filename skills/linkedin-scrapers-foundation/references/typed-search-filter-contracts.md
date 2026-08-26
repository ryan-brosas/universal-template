<!-- capsule-v2 -->
# Typed filter interfaces + enum vocabularies — how do I expose search filters as a typed API instead of raw query strings?

**Source:** linkedin-private-api MIT `master@e083f37`; Codebase Memory `linkedin-private-api`. **Question:** what is the canonical filter surface for people/job search, and which wire values must a porter copy verbatim?

## The filter contracts
**Path/Symbol:** `src/types/people-search-filters.ts:PeopleSearchFilters` (:5–20); `src/types/job-search-filters.ts:JobSearchFilters` (:4–14); enums `network.enum.ts` (F|S|O), `search-type.enum.ts` (PEOPLE|COMPANIES|JOBS), `search-result-type.enum.ts` (SEARCH_HITS|SEARCH_FEATURES), `job-type.enum.ts` (F/C/P/T/I/V/O), `experience.enum.ts` ('1'..'6').
**Signature:** `interface PeopleSearchFilters { currentCompany?, pastCompany?, company?, geoUrn?, industry?, network?: LinkedInNetworkType|[..], profileLanguage?, school?, connectionOf?, contactInterest?, serviceCategory?, firstName?, lastName?, title? }`; `JobSearchFilters { companies?, experience?, jobType?, jobTitle?, industries?, location?, remote?: boolean, listed_at?: number, distance?: number }`.
**Data Shape:** every list-capable field is `string | string[]` — the paramsSerializer (voyager-filter-grammar-serializer) accepts both shapes; enum members ARE the wire tokens (single letters/digits), so the TS union doubles as protocol documentation.

### Decisive source
```ts
// derived convenience APIs are FILTER REWRITES at the type level:
searchOwnConnections({ filters }: { filters?: Omit<PeopleSearchFilters, 'network'> }) {
  return new PeopleSearchScroller({ ..., filters: { ...filters, network: LinkedInNetworkType.F } });
}
// jobs wire values are single-letter/digit enums, NOT words:
enum LinkedInJobType { FULL_TIME='F', CONTRACT='C', PART_TIME='P', TEMPORARY='T', INTERNSHIP='I', ... }
enum LinkedInExperienceType { INTERNSHIP='1', ENTRY='2', ASSOCIATE='3', MID_SENIOR='4', DIRECTOR='5', EXECUTIVE='6' }
```

**Flow:** caller passes typed filters → repository injects scope rewrites (`network:F` for own connections; `+connectionOf:profileId` for someone else's) → request layer merges `{...filters, resultType}` and serializes via the List() grammar → server returns clusters filtered by `SearchResultType.SEARCH_HITS` (features clusters are silently dropped).
**Invariant:** `Omit<PeopleSearchFilters,'network'>` on searchOwnConnections makes the scope rewrite UNEXPRESSIBLE from outside — port that type-level guard, not just the spread; experience/jobType enums are positional digit/letter codes where dropping the quotes ('1' vs 1) changes serialization. `BlendedSearchFilters = PeopleSearchFilters | { resultType? }` — resultType is reserved for the wire layer.
**Probe:** source-grounded (no dedicated spec file for types): `test/search/search-repository.spec.ts:551–573` drives `{location:'Israel', experience:'1'}` through searchJobs asserting the serialized param dict round-trips; :212 pins own-connections network-F injection. Graph probe: `search_graph --query "PeopleSearchFilters JobSearchFilters enum"` resolves both interfaces.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "linkedin-private-api", query: "PeopleSearchFilters JobSearchFilters LinkedInNetworkType", limit: 10 });
```

## Verdict
Adopt typed-filter-over-query-string with Omit-based scope locking and letter/digit enum vocabularies copied verbatim (they are LinkedIn's stable wire codes). Adapt field sets per API generation (facet availability drifts). Contrast in-suite: EasyApplyJobsBot encodes the same f_E=1..6 / f_JT=F..O vocabularies as string-matched URL builders (search-url-builder) — this repo shows the same protocol as a type system.
