<!-- capsule-v2 -->
# Partner enrollment filter materialization — how do partner-facing routes turn arbitrary link filters into enrollment-scoped ones without leaking other partners' links?

**Source:** dub AGPL-3.0 `main@29df217a29631ced4041882a28d2327cc4546f27`; Codebase Memory `dub`. **Question:** When the caller may pass `linkId` (even NOT IN), `domain+key`, or nothing, how does a route guarantee the eventual query only ever touches THAT partner's enrollment links?

## The repeated materialization prelude
**Path/Symbol:** `apps/web/app/(ee)/api/partner-profile/programs/[programId]/analytics/export/route.ts:GET` (:63-:132); identical block in `.../events/route.ts:GET` (:58-:109).
**Signature:** inside `withPartnerProfile(async ({ partner, params, searchParams }) => ...)` after `getProgramEnrollmentOrThrow({ partnerId, programId, include: { program: true, links: true } })`.
**Data Shape:** `parsedParams.linkId` is a `ParsedFilter` (`{operator, sqlOperator:"IN"|"NOT IN", values}`); `links` is the full enrollment-link list; output is always an `IN` ParsedFilter over concrete ids.

### Decisive source
```ts
if (!linkId.values.every((value) => links.some((link) => link.id === value))) {
  throw new DubApiError({ code: "not_found", message: "One or more links are not found" });
}
if (linkId.sqlOperator === "NOT IN") {
  const finalIncludedLinkIds = links
    .filter((link) => !linkId.values.includes(link.id))
    .map((link) => link.id);
  ...
  parsedParams.linkId = { operator: "IS", sqlOperator: "IN", values: finalIncludedLinkIds };
}
```

**Flow:** fetch enrollment + links once → membership-validate every requested `linkId` value against enrollment links → **materialize NOT IN into an explicit IN** over all non-excluded enrollment ids (empty remainder ⇒ early exit) → else resolve `domain+key` by scanning enrollment links → fall through to the size branch below.
**Invariant:** the warehouse query must NEVER receive a raw NOT IN from a partner context — negation is computed against the trusted enrollment set so exclusions can't widen scope. Membership validation doubles as an existence oracle scoped to the enrollment (a valid-but-foreign link id reads as `not_found`, never `forbidden`).
**Probe:** no direct unit test for these routes at pin (coverage caveat). Anchors observed live in analytics/export route: `NOT IN` :81, membership check chain :75-:80; events twin :64-:65.

## Large-program escape hatch
**Path/Symbol:** same two routes (:49-:55 / :34-:42) + `apps/web/lib/constants/partner-profile.ts:LARGE_PROGRAM_IDS`.
**Data Shape:** gate = `LARGE_PROGRAM_IDS.includes(program.id) && toCentsNumber(totalCommissions) < LARGE_PROGRAM_MIN_TOTAL_COMMISSIONS_CENTS`.

### Decisive source
```ts
getAnalyticsParams: () =>
  parsedParams.linkId
    ? { linkId: parsedParams.linkId }
    : links.length > MAX_PARTNER_LINKS_FOR_LOCAL_FILTERING
      ? { partnerId: partner.id }
      : { linkId: parseFilterValue(links.map((link) => link.id)) },
```

**Flow:** explicit linkId wins → else if enrollment is small, enumerate ALL link ids into an IN filter → else pass `partnerId` and let Tinybird-side scoping do the work. Both routes share this exact ternary (events route :104-:108).
**Invariant:** id-enumeration is bounded by `MAX_PARTNER_LINKS_FOR_LOCAL_FILTERING` — the fallback for big enrollments is a COARSER trusted scope (partnerId), never an unbounded IN.
**Probe:** anchors observed live: analytics/export :127-:131 ternary, `LARGE_PROGRAM_IDS.includes(program.id)` :50, `ratelimit(1, "30 s")` :27 (export-only throttle); events route :106. Nearest executed tests: `tests/analytics/partners/analytics.test.ts` (CI-gated, describe.runIf(env.CI) :9-10).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dub", query: "partner profile programId analytics export", limit: 10 });
await mcp.codebase_memory.get_code_snippet({ project: "dub", qualified_name: "dub.apps.web.app.(ee).api.partner-profile.programs.[programId].analytics.export.route" });
```

## Verdict
Adopt: negate-then-materialize against a trusted ownership set; membership-check requested ids with a scoped not_found; bounded enumeration with coarse-scope fallback. Adapt the gate constants and the ParsedFilter shape to your filter model; omit dub's specific LARGE_PROGRAM_IDS allowlist (it is a per-deployment ops lever). Coverage caveat: no direct unit test covers either route at pin; behavior pinned by source anchors + CI-gated sibling test.
