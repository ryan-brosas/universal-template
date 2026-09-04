<!-- capsule-v2 -->
# Workspace customers export defer twin — what does the THIRD member of the threshold-defer family do differently from links/events?

**Source:** dub AGPL-3.0-or-later `main@29df217a2963`; Codebase Memory `dub`. **Question:** How does a deferred export combine the program-twins publisher posture with a payouts-style hard row cap, and why must the generator strip presentation columns before paging?

## Connected graph-selected seam
**Path/Symbol:** `apps/web/app/(ee)/api/customers/export/route.ts:GET` (:16-72) · `apps/web/app/(ee)/api/cron/export/customers/route.ts:POST` (:19-99) · `apps/web/lib/customers/api/fetch-customers-batch.ts:fetchCustomersBatch` (:7-32).
**Signature:** `GET = withWorkspace(..., { requiredPlan: ["business","advanced","enterprise"] })`; `POST = withCron(...)`; `fetchCustomersBatch(filters, pageSize = 1000)`.
**Data Shape:** Publisher body: raw filters + workspaceId + programId + userId + `columns.join(",")`. Worker caps at `MAX_CUSTOMERS_EXPORT_LIMIT = 100_000` (:14).

### Decisive source
```ts
// PUBLISHER — program-twins-shaped threshold defer, with workspace-side PROGRAM PINNING:
if (programId || partnerId) { programId = getDefaultProgramIdOrThrow(workspace); }  // :22-24 arbitrary query programId NEVER honored
const count = await prisma.customer.count({ where: buildCustomerCountWhere({...}) }); // :26-34 shared builder
if (count > MAX_CUSTOMERS_TO_EXPORT) { /* publish raw + columns.join(",") */ return NextResponse.json({}, { status: 202 }); }

// WORKER — payouts-style ROW CAP inside the drain loop:
const remaining = MAX_CUSTOMERS_EXPORT_LIMIT - allRows.length;   // :60
if (remaining <= 0) break;                                       // :62-64
allRows.push(...formatted.slice(0, remaining));                  // :66 TRUNCATION, not rejection
const capped = allRows.length >= MAX_CUSTOMERS_EXPORT_LIMIT ? ` (capped at ${MAX_CUSTOMERS_EXPORT_LIMIT})` : "";  // :91-94 honest log

// GENERATOR — sixth full-page sibling; strips presentation before paging:
const { columns: _columns, ...filtersRest } = filters;           // :11 columns ≠ query shape
hasMore = customers.length === pageSize;                         // :27
```

**Flow:** pin program → count probe through buildCustomerCountWhere (dimension self-exclusion inherited) → ≤1000 inline CSV / >1000 QStash 202 → worker re-derives user-with-email + workspace(name) by raw ids (SHALLOW depth like events/workspace twin — customer exports need no RBAC materialization) → drain generator, truncating at 100k rows → CSV → storage → email with an honest "(capped at N)" completion log.
**Invariant:** The hybrid proves the two known postures compose: threshold-defer decides INLINE-vs-WORKER; a worker-side budget cap decides HOW MANY rows ever leave. Truncation is silent to the user's CSV but explicit in the ops log. Workspace routes overwrite any caller-supplied programId with the workspace's defaultProgramId (missing ⇒ not_found "Program not found") — query params can never widen scope. The generator strips `columns` because requested output fields are not filterable dimensions.
**Probe:** No direct test for this plane (tests/**/*customer* = ∅). Deterministic probes: pin guard :22-24, MAX_CUSTOMERS_TO_EXPORT=1000 :13/:36, status 202 :48, requiredPlan :70; worker cap constant :14, slice-truncation :60-66, capped-suffix :91-94; generator column-strip :11 + hasMore===pageSize :27.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dub", qn_pattern: ".*customers.*(export|fetch).*", name_pattern: "^(GET|POST)$" });
```

## Verdict
Adopt the composition: threshold-defer for latency, worker-side cap for cost bounding, honest capping in logs. Adapt the 100k ceiling to your storage/queue economics and decide per resource whether truncation should also notify the user inline. Omit the program-pinning overwrite only if your tenants have exactly one legal program scope enforced upstream.
