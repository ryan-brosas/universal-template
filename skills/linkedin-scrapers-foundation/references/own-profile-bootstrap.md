<!-- capsule-v2 -->
# Own-profile bootstrap + headline company join — resolve "me" through the mini-profile, attach the current company by headline match (how do I identify the authenticated account and enrich profiles without a second call)?

**Source:** linkedin-private-api MIT `master@e083f37`; Codebase Memory `linkedin-private-api`. **Question:** How does the client discover the logged-in identity, and how are profiles enriched with their current company from a single envelope?

## Two seams in one repository
**Path/Symbol:** `src/repositories/profile.repository.ts:getOwnProfile` (:53–63) and `getProfile` (:37–51).
**Signature:** `getOwnProfile(): Promise<Profile | null>` — GET `me`, find first `$type === MINI_PROFILE_TYPE` in `included[]`, then delegate to the FULL `getProfile(miniProfile)`; `getProfile({publicIdentifier})` → `identity/dash/profiles?q=memberIdentity&decorationId=...FullProfileWithEntities-35`.
**Data Shape:** Profile output = raw LinkedInProfile spread + `{company: LinkedInCompany | undefined, pictureUrls: string[]}`; pictureUrls derived as `rootUrl + artifact.fileIdentifyingUrlPathSegment` per artifact.

### Decisive source
```ts
async getOwnProfile(): Promise<Profile | null> {
  const response = await this.client.request.profile.getOwnProfile();
  const miniProfile = response?.included?.find(r => r.$type === MINI_PROFILE_TYPE);
  if (!miniProfile) { return null; }
  return this.getProfile(miniProfile);
}
// getProfile enrichment:
const profile = results.find(r => r.$type === PROFILE_TYPE && r.publicIdentifier === publicIdentifier);
const company = results.find(r => r.$type === COMPANY_TYPE && profile.headline.includes(r.name)) as LinkedInCompany;
```

**Flow (own-profile):** `/me` answers with a MINI profile only → null-safe miss returns `null` (never throws) → the mini's `publicIdentifier` feeds the full-profile call, so identity resolution reuses the same parse path as any other member. **Flow (company join):** within ONE envelope, pick the Profile row whose publicIdentifier matches, then match the Company row whose `name` appears INSIDE the profile's headline string — substring containment against the decoration-embedded entity.
**Invariant:** own-profile failure is data-shaped (`null`), not an exception — callers can branch on it. The company join is heuristic BY DESIGN: headline text is the only crosswalk between person and company rows in this projection; multiple name matches resolve to the FIRST found. Porters needing exact employer should use `*positionGroups`/geo entities instead (not modeled here — recorded as the boundary).
**Probe:** `test/profile/profile-repository.spec.ts` — getOwnProfile describe pins the me→miniProfile→getProfile chain via stubs (`requestUrl = new URL('me', linkedinApiUrl)`); getProfile tests pin `.company` equality (:40–58) and 4 derived pictureUrls (:60–77).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "linkedin-private-api", query: "getOwnProfile getProfile", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt: identity bootstrap via the mini-profile row + null-on-miss; single-envelope enrichment with explicit heuristics. Adapt the company crosswalk to position-group URNs when precision matters. Omit nothing. Direct tests pin both chains.
