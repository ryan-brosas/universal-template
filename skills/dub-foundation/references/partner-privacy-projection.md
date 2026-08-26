<!-- capsule-v2 -->
# Partner privacy projection — what may a partner see about the customers behind their own conversions?

**Source:** dub AGPL-3.0 `main@29df217a29631ced4041882a28d2327cc4546f27`; Codebase Memory `dub`. **Question:** How does a partner-facing events endpoint strip infrastructure metadata and conditionally de-identify customers AFTER authorization has already passed?

## Post-auth response shaping
**Path/Symbol:** `apps/web/app/(ee)/api/partner-profile/programs/[programId]/events/route.ts:GET` (:112-:143).
**Signature:** `events.map((event) => { const { ip, click, customer, ...eventRest } = event; const { ip: _, ...clickRest } = click; return {...}; })`.
**Data Shape:** input rows are full `getEvents` hydrations (event + click + customer + link); output rows carry `click` without `ip`, a zod-parsed customer subset, and `link` through `PartnerProfileLinkSchema.parse`.

### Decisive source
```ts
customer: z.object({
  id: z.string(),
  email: z.string(),
  ...(customerDataSharingEnabledAt && { name: z.string() }),
}).parse({
  ...customer,
  email: customer.email
    ? customerDataSharingEnabledAt
      ? customer.email
      : obfuscateCustomerEmail(customer.email)
    : customer.name || generateRandomName(),
  ...(customerDataSharingEnabledAt && {
    name: customer.name || generateRandomName(),
  }),
}),
```

**Flow:** auth + enrollment scoping pass FIRST (see partner-enrollment-filter-materialization) → THEN per-row: delete `ip` from event and click → customer email is passed through only if the PROGRAM enabled data sharing (`customerDataSharingEnabledAt` set), else obfuscated → customers with no email at all get `name` or a random placeholder so the row still renders → `name` field itself exists only under the sharing flag, filled with real name or random filler.
**Invariant:** projection is defense-in-depth BEHIND authz — even though every event already belongs to this partner's links, IP is never returned and PII passes only under an explicit program-level opt-in flag. The zod `.parse` doubles as a whitelist: anything not in the schema is dropped silently.
**Probe:** no direct unit test at pin (coverage caveat). Anchors observed live: `obfuscateCustomerEmail` import :4 / use :134, `customerDataSharingEnabledAt` :24/:127/:132/:136, `generateRandomName()` fallbacks :135/:137.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dub", query: "partner profile events route obfuscate customer", limit: 10 });
await mcp.codebase_memory.trace_path({ project: "dub", function_name: "obfuscateCustomerEmail", direction: "inbound", depth: 1 });
```

## Verdict
Adopt: per-row metadata stripping plus a flag-gated PII projection enforced by a strict parse at the boundary, with synthetic fillers so UI contracts never break. Adapt which fields count as PII and where the sharing flag lives; omit dub's specific email-obfuscation cosmetics (read `obfuscate-customer-email.ts` directly before porting its exact mask). Coverage caveat: behavior pinned by source anchors only; no direct unit test at pin.
