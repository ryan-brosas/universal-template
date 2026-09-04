<!-- capsule-v2 -->
# Events export worker twins — how does a deferred export worker re-derive authorization and enforce partner privacy OUTSIDE the HTTP boundary?

**Source:** dub AGPL-3.0-or-later `main@29df217a2963`; Codebase Memory `dub`. **Question:** When a large event export was deferred to QStash (threshold-export-defer), what must the WORKER re-derive before emitting rows — and which twin carries how much?

## Connected graph-selected seam
**Path/Symbol:** `apps/web/app/(ee)/api/cron/export/events/workspace/route.ts:POST` (:31-126) · `.../events/partner/route.ts:POST` (:39-220) · `.../events/fetch-events-batch.ts:fetchEventsBatch` (:4-26).
**Signature:** `export async function POST(req: Request)` ×2; `export async function* fetchEventsBatch(filters: Omit<EventsFilters,"page"|"limit">, pageSize: number = 1000)`.
**Data Shape:** Worker payload = publisher's raw searchParams + identity columns. Workspace twin extends `eventsQuerySchema` with `columns` (comma-split array), `workspaceId`, `userId`, optional `dataAvailableFrom` (`z.coerce.date()` :27). Partner twin extends `partnerProfileEventsQuerySchema` with `columns/partnerId/programId/userId`. Output: one CSV in storage + "export ready" email; `logAndRespond` skip strings for every degenerate case.

### Decisive source
```ts
// workspace twin: NO RBAC re-materialization at all — user+workspace existence only
const user = await prisma.user.findUnique({ where: { id: userId }, select: { email: true } });
if (!user?.email) return logAndRespond(`User ${userId} has no email. Skipping the export.`);
const workspace = await prisma.project.findUnique({ where: { id: filters.workspaceId }, ... });
...
dataAvailableFrom: z.coerce.date().optional(),   // :27 — publisher computed min(workspace.createdAt, programStartedAt)

// partner twin: replay the ENTIRE materialization prelude, then project privacy PER BATCH
if (!linkId.values.every((value) => links.some((link) => link.id === value))) return logAndRespond("One or more links are not found...");
if (linkId.sqlOperator === "NOT IN") { /* flip to explicit IN over all non-excluded enrollment links */ }
...(parsedParams.linkId ? { linkId: parsedParams.linkId }
  : links.length > MAX_PARTNER_LINKS_FOR_LOCAL_FILTERING
    ? { partnerId }
    : { linkId: parseFilterValue(links.map((link) => link.id)) }),
dataAvailableFrom: program.startedAt ?? program.createdAt,   // :139 — recomputed server-side
```

**Flow:** verify QStash signature → parse payload → re-fetch user (must exist WITH email) → [workspace twin: re-fetch workspace; done] / [partner twin: getProgramEnrollmentOrThrow({program,links}) → membership-validate linkId.values against enrollment links → NOT IN flips to explicit IN over all non-excluded ids (empty ⇒ skip) → domain+key resolved by scanning enrollment links] → `for await fetchEventsBatch` → per-row projection (partner twin strips `ip` from event AND click, strict-parses link via PartnerProfileLinkSchema, obfuscates/fills customer email+name under `customerDataSharingEnabledAt`) → column-project via `eventsExportColumnNames ?? capitalize(c)` + `eventsExportColumnAccessors[c]?.(row) ?? row?.[c]` (:85-86/:179-180) → convertToCSV → createDownloadableExport under `exports/events/{workspace|partner}/<random16>.csv` → email.
**Invariant:** Authorization is RE-DERIVED at execution time from raw ids in the queue message — a stale or forged payload cannot inherit an old session's scope. The workspace twin deliberately does NOT rebuild folder RBAC (validateLinksQueryFilters is absent from the file — negative probe verified this run): event filters carry no folderId so there is nothing to re-materialize. The partner twin enforces the SAME privacy projection as its HTTP route INSIDE the batch loop, so exports can never bypass it. Both twins bound results by data availability: workspace takes it from the trusted publisher payload, partner recomputes `program.startedAt ?? program.createdAt` server-side.
**Probe:** No direct test exists for either worker (glob `tests/**/*event*export*` = ∅ this run; integration suites are CI/cloud-gated). Deterministic probes: `payloadSchema` :20-28 with `dataAvailableFrom` :27; `includeMetadata:false` :133; `MAX_PARTNER_LINKS_FOR_LOCAL_FILTERING` ternary :136-138; `startedAt ?? createdAt` :139; generator `pageSize = 1000` :6 and `hasMore = events.length === pageSize` :21.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dub", query: "cron export events workspace partner worker route", limit: 10 });
await mcp.codebase_memory.trace_path({ project: "dub", function_name: "fetchEventsBatch", direction: "both", depth: 2 }); // callers_total=2: exactly the two workers; callees = getEvents/getLinksMap/getCustomersMap/transformLink feed-funnel stack
```

## Verdict
Adopt the two-depth authorization split: re-fetch actor identities always; rebuild expensive RBAC materialization ONLY where the filter shape demands it; never trust a queued payload's implied session. Adapt the projection hook location (here inside the drain loop) to your executor's row pipeline. Omit dub's QStash signature plumbing if your queue has its own verification primitive. Coverage caveat: both workers have no direct tests; anchors line-pinned from source reads at the cited pin.
