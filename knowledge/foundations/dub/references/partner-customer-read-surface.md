<!-- capsule-v2 -->
# Partner customers read surface — how do you show a partner THEIR customers without leaking tenant data or subsidizing unbounded reads?

**Source:** dub AGPL-3.0-or-later `main@29df217a2963`; Codebase Memory `dub`. **Question:** What gate, existence oracle, and projection does the partner-facing customer list/detail surface apply that the workspace-side twin does not?

## Connected graph-selected seam
**Path/Symbol:** `apps/web/app/(ee)/api/partner-profile/programs/[programId]/customers/route.ts:GET` (:22-117) · `.../customers/[customerId]/route.ts:GET` (:20-106) · `lib/analytics/get-customer-events.ts:getCustomerEvents` (:13-84).
**Signature:** `export const GET = withPartnerProfile(async ({ partner, params, searchParams }) => ...)`; `getCustomerEvents({ customerId, linkIds?, includeMetadata? = true })`.
**Data Shape:** List query: `{search?, country?, linkId?, sortBy, sortOrder, page=1, pageSize}`. Enrollment fetch returns `{program, links?, totalCommissions, customerDataSharingEnabledAt}`. Output rows = `PartnerProfileCustomerSchema.extend({name} when sharing)` over transformCustomer + activity envelope.

### Decisive source
```ts
// BOTH list and detail gate large programs behind lifetime commission volume
if (LARGE_PROGRAM_IDS.includes(program.id) &&
    toCentsNumber(totalCommissions) < LARGE_PROGRAM_MIN_TOTAL_COMMISSIONS_CENTS) {
  throw new DubApiError({ code: "forbidden", message: "This feature is not available for your program." }); // :44-53 / :33-41
}
// detail route's DOUBLE existence oracle: tenant match FIRST, attribution SECOND
if (!customer || customer?.projectId !== program.workspaceId) {
  throw new DubApiError({ code: "not_found", message: "Customer is not part of this program." });        // :62-67
}
const events = await getCustomerEvents({ customerId: customer.id, linkIds: links.map((l) => l.id), includeMetadata: false });
if (events.length === 0) {
  throw new DubApiError({ code: "not_found", message: "Customer is not attributed to any links by this partner." }); // :75-80
}
const firstLinkId = events[events.length - 1].link_id; // :83 — "first interaction" = LAST row of the pipe's ordering
// search exists ONLY when data sharing enabled; @ ⇒ exact email else MySQL full-text on email+name
...(search && customerDataSharingEnabledAt
  ? search.includes("@") ? { email: search }
  : { email: { search: sanitizeFullTextSearch(search) }, name: { search: sanitizeFullTextSearch(search) } }
  : {}),
```

**Flow:** enrollment scope → LARGE_PROGRAM gate (`LARGE_PROGRAM_IDS.includes(id) && totalCommissions(cents) < $5000` ⇒ forbidden) → [list: scoped findMany folding firstSaleAt via a take:1 ascending sale-commission include IN THE SAME QUERY] / [detail: findUnique → tenant-match oracle → getCustomerEvents over the partner's enrollment link ids → attribution oracle → firstLinkId from last event] → per-row projection: `firstSaleAt ?? null`, flag-gated email obfuscation or `customer.name || generateRandomName()` filler, name exposed only under `customerDataSharingEnabledAt`, strict zod parse exit.
**Invariant:** A partner may only see customers attributable to their own enrollment links (attribution oracle), only inside the correct workspace (tenant oracle), and both features can be volume-gated off for big programs below a spend floor. Privacy projection (obfuscate/fill/name-gate) rides ON TOP of auth at serialization time, enforced by strict parse. getCustomerEvents hydrates links MySQL-first with DROP-on-miss (drift tolerance) and repairs domain/key/timestamp from MySQL (:41-44); its row ORDER comes from Tinybird pipe `v2_customer_events`, whose parameters/data are `z.any()` TODO stubs (:6-7) — ordering lives in external SQL and must be re-verified there before relying on `events[length-1]`.
**Probe:** No tests exist for any partner-profile route (glob `tests/**/*partner-profile*/**` = ∅ this run). Deterministic probes: gate constants `LARGE_PROGRAM_IDS`/:47 + `LARGE_PROGRAM_MIN_TOTAL_COMMISSIONS_CENTS` (=500000 cents) via `lib/constants/partner-profile.ts`; includes("@") :65; sanitizeFullTextSearch :68-69; firstSaleAt fold :100 (list) / :92 (detail); not-found messages :65/:78; `events[events.length - 1].link_id` :83.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dub", qn_pattern: ".*partner-profile.*customers.*", name_pattern: "^(GET|POST)$", limit: 10 }); // exactly 3 routes: list :22-117, count :15-133, detail :20-106
await mcp.codebase_memory.trace_path({ project: "dub", function_name: "getCustomerEvents", direction: "inbound", depth: 1 }); // callers_total=2: workspace customers/[id]/activity + this detail route
```

## Verdict
Adopt the three-layer partner read posture: enrollment-scoped where-clause, cost/volume feature gate, then serialization-time privacy projection with strict-parse enforcement; adopt the double existence oracle (tenant ≠ attribution) with two distinct teaching messages. Adapt the $5000 commission-floor gate to your own abuse-economics constant. Omit dub's Tinybird dependency if your event store answers attribution directly — but keep row ordering pinned somewhere explicit, because the first-attribution heuristic consumes it.
