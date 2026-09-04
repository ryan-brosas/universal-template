<!-- capsule-v2 -->
# Voyager payload extraction — how are profile identities parsed from LinkedIn's `included` array and X's `UserByScreenName` without brittle DOM scraping?

**Source:** growchief AGPL-3.0 `main@abb1e37a`; Codebase Memory `growchief`. **Question:** what normalization contract turns raw authenticated-API JSON into `{firstName, lastName, picture, degree, pending}` / `{id, name, picture}` across the two providers?

## `$type` suffix matching + vectorImage widest-artifact pick + URN tail as id
**Path/Symbol:** `shared/server/bots/providers/linkedin/extract.my.profile.ts:extractMyProfile` (:1-54) + `bestVectorUrl` (:32-41); `extra.person.profile.ts:extractConnectionTarget` (:1-34); X twin `shared/server/bots/providers/x/extract.person.profile.ts:extractUserData` (:8-36); lead-list twin `linkedin.provider.ts:leadList` (:66-135).
**Signature:** `extractMyProfile(payload) → {id, name, picture} | false`; `extractConnectionTarget(payload) → {firstName, lastName, degree, pending}`; `extractUserData(userData) → {firstName, lastName, picture, degree, pending:false}`.
**Data Shape:** LinkedIn payloads are voyager-style `{included: [{$type, entityUrn, firstName…}]}`; profile objects matched by `x.$type.endsWith('.identity.profile.Profile')`; target selection matches `entityUrn === elements[0]` from `identityDashProfilesByMemberIdentity['*elements']`; pictures ride `vectorImage.artifacts[].fileIdentifyingUrlPathSegment`.

### Decisive source
```ts
// extract.my.profile.ts — id ladder: numeric member urn → publicIdentifier → entityUrn tail
const memberId =
  profile.objectUrn?.split(':').pop() ||
  profile.publicIdentifier ||
  profile.entityUrn?.split(':').pop() || null;
// bestVectorUrl — widest artifact wins:
const best = vec.artifacts.slice().sort((a, b) => (b.width||0) - (a.width||0))[0];
```

**Flow (leadList replay):** capture the search-results API response by its stable hash (`waitForResponse(/5ba32757c00b31aea747c8bebb92855c/)`) → clone method/headers/postData → in-page fetch replays it ten times rewriting `start:\d*` to 0..90 → map `included` rows that carry `navigationUrl`, splitting names on first space, stripping query/hash from profile URLs → `uniqBy(url)` dedupe with a break on any empty page. Degree/pending for a TARGET profile come from string-scanning the WHOLE payload for `DISTANCE_(\d)` / `PENDING`. X's extractor reads `relationship_perspectives` directly and rewrites avatar URL `'normal'→'200x200'` for higher resolution.

**Invariant:** extraction is total-but-lenient — every field access chains optionals and falls back to ''/false/degree-default rather than throwing, because these run inside browser races where a thrown extractor loses the race silently; the ONE hard failure is `extractMyProfile` returning literal `false` when no Profile-typed object exists (login verification depends on that distinction). Name-splitting convention everywhere: `first = parts[0]`, `last = rest.join(' ')`. The hash-based response matchers are content-addressed endpoints that survive UI redesigns but rotate across API versions — treat them as config, not code.

**Probe:** deterministic pins from repo root: `grep -nF 'endsWith' shared/server/bots/providers/linkedin/extract.my.profile.ts` → :17; `grep -cF 'DISTANCE_' shared/server/bots/providers/linkedin/extra.person.profile.ts` → 2; `grep -nF '200x200' shared/server/bots/providers/x/extract.person.profile.ts` → :14; `grep -nF '[0, 10, 20, 30, 40, 50, 60, 70, 80, 90]' shared/server/bots/providers/linkedin/linkedin.provider.ts` → :93; `grep -nF 'start:' shared/server/bots/providers/linkedin/linkedin.provider.ts` → :94.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "growchief", query: "extractMyProfile bestVectorUrl vectorImage", limit: 10 });
```

## Verdict
Adopt $type-suffix matching, widest-artifact image picks, URN-tail ids, lenient-chain normalization, and start-offset replay pagination; adapt hashes/paths per API version; omit nothing behavioral. Coverage caveat: deterministic probes only.
