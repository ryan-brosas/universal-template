<!-- capsule-v2 -->
# Program export worker twins — how do partner/commission exports differ from the payout export that trims to a budget?

**Source:** dub AGPL-3.0-or-later `main@29df217a2963`; Codebase Memory `dub`. **Question:** Two deferred exports share the threshold-defer publisher shape — when does one worker cap rows and the other page until exhaustion?

## Connected graph-selected seam
**Path/Symbol:** `apps/web/app/(ee)/api/cron/export/partners/route.ts:POST` (:23-114) · `.../cron/export/commissions/route.ts:POST` (:23-114) · publishers `app/(ee)/api/partners/export/route.ts:GET` (:15-63) and `app/(ee)/api/commissions/export/route.ts:GET` (:15-63) · generators `fetch-partners-batch.ts:fetchPartnersBatch` (:12-40), `fetch-commissions-batch.ts`.
**Signature:** `POST(req)` workers; `GET = withWorkspace(..., { requiredPlan: ["business","advanced","enterprise"] })` (partners publisher; commissions publisher omits requiredPlan); `fetchPartnersBatch({filters, columns, pageSize = 1000})`.
**Data Shape:** Publisher body = raw parsed params + `columns: columns.join(",")` + `programId` + `userId`; count probe strips groupBy (`getPartnersCount({...filters, groupBy: undefined, programId})` :22-26) or reads `counts.all.count` (commissions :29).

### Decisive source
```ts
const MAX_PARTNERS_TO_EXPORT = 1000;                       // :12 — publisher-side threshold
if (partnersCount > MAX_PARTNERS_TO_EXPORT) {              // :29
  await qstash.publishJSON({ url: `.../api/cron/export/partners`,
    body: { ...parsedParams, columns: columns.join(","), programId, userId: session.user.id } });
  return NextResponse.json({}, { status: 202 });           // :40
}
includeGroup: columns.includes("group"),                   // generator :29 — join planned FROM REQUESTED COLUMNS
hasMore = partners.length === pageSize;                    // :35 — full-page ⇒ maybe-more

// WORKER side: re-fetch user-with-email + program, then drain with NO row cap:
for await (const { partners } of fetchPartnersBatch({ filters: { ...filters, programId }, columns })) {
  allPartners.push(...formatPartnersForExport(partners, columns));
}
```

**Flow:** publisher pins workspace's default program (`getDefaultProgramIdOrThrow`) → count probe → ≤1000 renders inline CSV / >1000 publishes raw filters and returns 202 → worker verifies QStash signature, re-fetches user (with email) + program by raw ids → drains the full-page async generator → per-batch column formatting → CSV → storage → email.
**Invariant:** These twins are PROGRAM-scoped and UNBUDGETED: unlike payout-export-split's worker (remaining-budget trim at 100k rows), neither partner nor commission worker caps output — negative probe `budget|REMAINING` over app/(ee)/api/cron/export returns ZERO matches this run; they page until a partial page ends the loop. The group join exists only if the requested export columns demand it. Worker authorization is re-derived from ids exactly like the events/workspace twin (shallow depth: user+program existence, no RBAC rebuild).
**Probe:** No direct tests for these four routes/generators (coverage caveat). Deterministic probes: MAX_PARTNERS_TO_EXPORT :12, columns.join(",") :34, status 202 :40, requiredPlan :61 (partners publisher); MAX_COMMISSIONS_TO_EXPORT :12 + counts.all.count :29 (commissions publisher); includeGroup :29 + hasMore :35 (generator); formatCommissionsForExport/fileKey anchors in format-commissions-for-export.ts + worker fileKey `exports/partners|commissions/<random16>.csv`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dub", qn_pattern: ".*(partners\\.export|commissions\\.export).*", name_pattern: "^(GET|POST)$" }); // publishers :15-63 each
await mcp.codebase_memory.get_code_snippet({ project: "dub", qualified_name: "dub.apps.web.app.(ee).api.cron.export.partners.route.POST" });
```

## Verdict
Adopt the family table posture: same publisher skeleton (threshold probe → 202 → raw-param message), but decide PER RESOURCE whether the worker caps (money-bearing exports get budget trims) or drains (directory-style exports). Adapt the plan gate to your tier model; note dub gates partners/export but not commissions/export. Omit the columns-planned joins only if your exporter fetches relations unconditionally and your DB tolerates it.
