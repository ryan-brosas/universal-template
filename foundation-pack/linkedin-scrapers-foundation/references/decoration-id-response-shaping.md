<!-- capsule-v2 -->
# DecorationId response-shaping — versioned `deco` params select which projection an endpoint returns (how do I request exactly the fields my parser expects)?

**Source:** linkedin-private-api MIT `master@e083f37`; Codebase Memory `linkedin-private-api`. **Question:** Voyager endpoints return different shapes for the same URL depending on a decoration parameter — how is it used, and what does it imply for parsers?

## The deco params
**Path/Symbol:** `src/requests/profile.request.ts:getProfile` (:12–22); `src/requests/search.request.ts:searchJobs` (:59); entity pins `src/entities/linkedin-profile.entity.ts`, `linkedin-job-posting.ts`.
**Signature:** GET params `{q: 'memberIdentity', memberIdentity: publicIdentifier, decorationId: 'com.linkedin.voyager.dash.deco.identity.profile.FullProfileWithEntities-35'}`; jobs: `'com.linkedin.voyager.deco.jserp.WebJobSearchHitLite-14'`.
**Data Shape:** the `-NN` suffix is a server-side template VERSION — bump it and included[] gains/loses `$type`s (e.g. FullProfileWithEntities returns Profile + Company + geo/locale sub-entities in one call).

### Decisive source
```ts
const queryParams = {
  q: 'memberIdentity',
  memberIdentity: publicIdentifier,
  decorationId: 'com.linkedin.voyager.dash.deco.identity.profile.FullProfileWithEntities-35',
};
return this.request.get<GetProfileResponse>('identity/dash/profiles', { params: queryParams });
```

**Flow:** client requests a named decoration → server expands that template into `data` + `included[]` rows → repository parses by `$type` consts, NOT by field presence — so a decoration bump only breaks parsing where a `$type` disappears. The profile company join depends on this: `results.find(r => r.$type === COMPANY_TYPE && profile.headline.includes(r.name))` (`profile.repository.ts:43`) works because FullProfileWithEntities embeds company entities.
**Invariant:** NEVER parse these responses positionally or by assuming every field exists — decorations are templates; code must filter `included[]` by exact `$type` and treat absent members as undefined (the repo's spread-joins do). Version suffixes are load-bearing: pin the one your fixtures were built against and diff shapes before bumping.
**Probe:** `test/profile/profile-repository.spec.ts:16–77` — stub keyed on the FULL param dict including decorationId; key-set assertion `difference(Object.keys(resultProfile), Object.keys(profile)).length === 0` plus `.company` populated proves the decoration delivered both entity types in one envelope.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "linkedin-private-api", query: "decorationId com.linkedin.voyager", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt "request a named projection, parse by $type" for any templated-projection API. Adapt decoration ids/versions per generation (they rotate). Contrast in-suite: open-linkedin-api passes equivalent deco strings inline (voyager-mutation-endpoints) — this repo isolates them as request-level constants paired with typed fixtures. Direct test pins the param dict verbatim.
